import aws_cdk as core
import aws_cdk.assertions as assertions

from lectionary_pdf_generator.lectionary_pdf_generator_stack import LectionaryPdfGeneratorStack

# example tests. To run these tests, uncomment this file along with the example
# resource in lectionary_pdf_generator/lectionary_pdf_generator_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = LectionaryPdfGeneratorStack(app, "lectionary-pdf-generator")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
