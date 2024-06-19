import logging

from bs4 import BeautifulSoup
import pymupdf
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_webpage(url: str) -> str:
	try:
		resp = requests.get(url)
	except requests.exceptions.RequestException as e:
		logger.exception(e)
		raise
	else:
		logger.info(resp.status_code)
		return resp.text
	
def extract_disciples_org(html: str) -> dict:
	disciples_bs4 = BeautifulSoup(html, 'html.parser')
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


def get_scripture_reference() -> str:
	url = "https://disciples.org/resources/lectionary/"
	html = get_webpage(url)
	data = extract_disciples_org(html)
	return data

def search_scripture(references: list[str], version: str = 'NIV') -> dict:
	result = []
	for ref in references:
		url = f"https://www.biblegateway.com/passage/?search={ref}&version={version}"
		page = get_webpage(url)
		scripture_bs4 = BeautifulSoup(page, 'html.parser')
		passage_content = scripture_bs4.find_all(class_="passage-content")

		paragraphs = []
		for content in passage_content:
			for p in content.find_all('p'):
				paragraphs.append(p.get_text())

		result.append({
			"scripture_reference": ref,
			"paragraphs": paragraphs,
		})
	return result

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
	writer = pymupdf.DocumentWriter(filename)
	pno = 0 # current page number
	more = 1  # will be set to 0 when done
	while more:  # loop until all story content is processed
		dev = writer.begin_page(MEDIABOX)  # make a device to write on the page
		more, filled = story.place(WHERE)  # compute content positions on page
		story.element_positions(recorder, {"page": pno})  # provide page number in addition
		story.draw(dev)
		writer.end_page()
		pno += 1  # increase page number
	writer.close()  # close output file
	logger.info(f"File saved: {filename}")
	return filename


def recorder(elpos):
  pass


def lambda_handler(event, context):
	# This lambda function is going to create a pdf file with the weekly Lectionary content.
	# Step 1: get scripture reference from https://disciples.org/resources/lectionary/
	# Step 2: use the reference, search scripture from Bible Gateway and store in memory
	# Step 3: write the data to a pdf document
	# Step 4: send ses email with attached pdf file

	data = get_scripture_reference()
	scriptures = search_scripture(data['scripture_references'])

	story = generate_pdf_story({
		'title': data['lectionary_date'],
		'content': scriptures,
	})
	filename = write_pdf_doc(story)

	return {
		'result': 200
	}


if __name__ == '__main__':
	lambda_handler({}, {})