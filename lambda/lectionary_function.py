import logging
import os

import boto3
import pymupdf
import requests
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def request_webpage(url: str) -> str:
	try:
		resp = requests.get(url)
	except requests.exceptions.RequestException as e:
		logger.exception(e)
		raise
	else:
		logger.info(resp.status_code)
		return resp.text
	
def parse_html_to_beautifulsoup(html: str) -> BeautifulSoup:
	return BeautifulSoup(html, 'html.parser')
	
def extract_lectionary_resources(html: str) -> dict:
	disciples_bs4 = parse_html_to_beautifulsoup(html)
	lectionary_item = disciples_bs4.find(
			'div', 
			class_='disciples-lectionary-container'
		).find(
			'div', 
			class_='lectionary-item'
		)
	lectionary_date = lectionary_item.find('div', class_='lectionary-date').string
	lectionary_verses = lectionary_item.find_all('a', 'scripture-link')
	scripture_references = [v.string for v in lectionary_verses]
	return {
		'lectionary_date': lectionary_date,
		'scripture_references': scripture_references,
	}


def get_lectionary_page() -> str:
	url = "https://disciples.org/resources/lectionary/"
	html = request_webpage(url)
	return html

def search_scripture(references: list[str], version: str = 'NIV') -> dict:
	scriptures = []
	for ref in references:
		url = f"https://www.biblegateway.com/passage/?search={ref}&version={version}"
		html = request_webpage(url)
		scripture_bs4 = parse_html_to_beautifulsoup(html)
		passage_content = scripture_bs4.find_all(class_="passage-content")

		paragraphs = []
		for content in passage_content:
			for p in content.find_all('p'):
				paragraphs.append(p.get_text())

		scriptures.append({
			"scripture_reference": ref,
			"paragraphs": paragraphs,
		})
	return scriptures

def generate_pdf_story(data: dict) -> pymupdf.Story:
	my_template = ("""
	<body>
		<div id='title'></div>
		<div class='scripture-container'>
			<div class='scripture-header'></div>
			<div class='scripture-content'></div>
		</div>
	</body>""")
	my_css = ("""
	body {
		font-size: 15px;
		line-height: 1.5;
	}
	#title {
	  text-align: center;
	  font-size: 1.3em;
	  font-weight: bold;
	}
	.scripture-header {
	  font-size: 1.1em;
	  text-decoration: underline;
	}
	""")

	story = pymupdf.Story(html=my_template, user_css=my_css)
	body = story.body
	body.find(None, "id", "title").add_text(data['title'])
	container_template = body.find(None, "class", "scripture-container")

	for scr in data['content']:
		container = container_template.clone()
		container.find(None, 'class', 'scripture-header').add_text(scr['scripture_reference'])
		
		for para in scr['paragraphs']:
			p = container.add_paragraph()
			p.add_text(para)

		body.append_child(container)
	
	return story


def write_pdf_doc(story: pymupdf.Story) -> str:
	MEDIABOX = pymupdf.paper_rect("letter")  # size of a page
	WHERE = MEDIABOX + (36, 36, -36, -36)  # leave borders of 0.5 inches

	filename = "sample_output.pdf"
	writer = pymupdf.DocumentWriter(f"/tmp/{filename}")
	pno = 0 # current page number
	more = 1  # will be set to 0 when done
	while more:
		dev = writer.begin_page(MEDIABOX)
		more, filled = story.place(WHERE)
		story.element_positions(recorder, {"page": pno})
		story.draw(dev)
		writer.end_page()
		pno += 1
	writer.close()
	logger.info(f"File saved: {filename}")
	return filename


def recorder(elpos):
  pass


def compose_email(filename: str) -> MIMEMultipart:
	sender = os.environ["SENDER_EMAIL"]
	recipient = os.environ["RECIPIENT_EMAIL"]

	BODY_TEXT = "Hello,\r\nThis is an automated email.\r\nPlease see the attached file for this week's lectionary.\n\nCheers,\nAWS SES Bot"
	BODY_HTML = """
	<html>
	<head></head>
	<body>
	<p>Hello,</p>
	<p>This is an automated email.<br>Please see the attached file for this week's lectionary.</p>
	<p>Cheers,<br>AWS SES Bot</p>
	</body>
	</html>
	"""
	CHARSET = "UTF-8"

	msg = MIMEMultipart('mixed')
	msg['Subject'] = f"Lectionary - {filename}"
	msg['From'] = sender
	msg['To'] = recipient

	msg_body = MIMEMultipart('alternative')
	textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
	htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)

	msg_body.attach(textpart)
	msg_body.attach(htmlpart)
	
	att = MIMEApplication(open(f"/tmp/{filename}", 'rb').read())
	att.add_header('Content-Disposition','attachment',filename=filename)

	msg.attach(msg_body)
	msg.attach(att)
	return msg


def send_ses_raw_email(raw_message: MIMEMultipart) -> str:
	ses_client = boto3.client("ses")
	try:
		response = ses_client.send_raw_email(
			Source=raw_message['From'],
			Destinations=raw_message['To'],
			RawMessage={
				"Data": raw_message.as_string(),
			},
		)
    # Display an error if something goes wrong.	
	except ClientError as e:
		logger.exception(e.response['Error']['Message'])
		raise
	else:
		logger.info(f"Email sent! Message ID: {response['MessageId']}"),
		return response['MessageId']


def lambda_handler(event, context):
	# This lambda function is going to create a pdf file with the weekly Lectionary content.
	# Step 1: get scripture reference from https://disciples.org/resources/lectionary/
	# Step 2: use the reference, search scripture from Bible Gateway and store in memory
	# Step 3: write the data to a pdf document
	# Step 4: send ses email with attached pdf file

	html = get_lectionary_page()
	lectionary = extract_lectionary_resources(html)

	scriptures = search_scripture(lectionary['scripture_references'])

	story = generate_pdf_story({
		'title': lectionary['lectionary_date'],
		'content': scriptures,
	})
	filename = write_pdf_doc(story)

	msg = compose_email(filename)
	message_id = send_ses_raw_email(msg)
	return {
		'message_id': message_id
	}


if __name__ == '__main__':
	lambda_handler({}, {})