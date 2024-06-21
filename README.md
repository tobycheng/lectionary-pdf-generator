
# Lectionary PDF Generator

This is a project that fetches weekly Lectionary from [disciples.org](https://disciples.org/resources/lectionary/),
uses the scripture references to search from the [BibleGateway.com](https://www.biblegateway.com/), write the results to
 a PDF file and finally send the file attached to an e-mail.

 AWS Services used:
 - CloudFormation
 - Lambda Function
 - Systems Manager
 - Simple Email Service (SES)
 - EventBridge Cron Schedule

## Dependencies

- AWS account
- Create email variable at the Systems Manager Parameter Store
- [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
- [Poetry](https://python-poetry.org/docs/#installation)

## Deploy

with virtual environment activated
```
cdk deploy
```
OR with poetry 
```
poetry run cdk deploy
```

## Other CDK Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## Email Screenshot

![Email screenshot](sample_email_screenshot.png)