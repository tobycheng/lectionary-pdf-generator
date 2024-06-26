import aws_cdk as core
import aws_cdk.assertions as assertions

from lectionary_pdf_generator.lectionary_pdf_generator_stack import LectionaryPdfGeneratorStack

def test_synthesizes_template():
    app = core.App()
    stack = LectionaryPdfGeneratorStack(app, "lectionary-pdf-generator")
    template = assertions.Template.from_stack(stack)

    # Lambda Layer Created
    template.resource_count_is("AWS::Lambda::LayerVersion", 1)
    template.has_resource(
        "AWS::Lambda::LayerVersion",
        {
            "Properties": {
                "CompatibleRuntimes": [
                    "python3.12"
                ],
                "Description": "Dependencies Layer"
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete",
        }
    )

    # EventBridge Rule Created
    template.resource_count_is("AWS::Events::Rule", 1)
    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "ScheduleExpression": "cron(0 12 ? * MON *)",
        }
    )

    # Gives permission to event rule to invoke the lambda function
    template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "Principal": "events.amazonaws.com",
        }
    )

    # Lambda Function Created
    env_var_capture = assertions.Capture()
    template.resource_count_is("AWS::Lambda::Function", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "lectionary_function.lambda_handler",
            "MemorySize": 512,
            "Runtime": "python3.12",
            "Timeout": 30,
            "Environment": {
                "Variables": env_var_capture
            }
        }
    )

    # Assert Parameters
    env_var = env_var_capture.as_object()
    template.has_parameter(
        env_var["SENDER_EMAIL"]["Ref"],
        {
            "Type": "AWS::SSM::Parameter::Value<String>",
            "Default": "sender_email"
        }
    )
    template.has_parameter(
        env_var["RECIPIENT_EMAIL"]["Ref"],
        {
            "Type": "AWS::SSM::Parameter::Value<String>",
            "Default": "recipient_email"
        }
    )


    # Lambda function's execution role
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com",
                        },
                    },
                ],
                "Version": "2012-10-17"
            },
        }
    )

    # The function's execution role policy
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            # Allow function to execute SES SendRawEmail
            "PolicyDocument": {
                "Statement": [
                    {
                        "Action": "SES:SendRawEmail",
                        "Effect": "Allow",
                        "Resource": "*"
                    }
                ],
            }
        }
    )
