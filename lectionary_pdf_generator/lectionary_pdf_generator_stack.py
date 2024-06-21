import os
import subprocess

from aws_cdk import (
    aws_iam as iam,
    aws_events as events,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    aws_events_targets as targets,
    Duration,
    Stack,
    RemovalPolicy,
)
from constructs import Construct

class LectionaryPdfGeneratorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # install dependencies to the lambda layer
        requirements_file = "lambda/requirements.txt"
        output_dir = f".build"

        if not os.environ.get("SKIP_PIP"):
            subprocess.check_call(
                f"pip install -r {requirements_file} -t {output_dir}/python/".split()
            )
            # pymupdf need to be handled differently
            # More on: https://github.com/pymupdf/PyMuPDF/issues/430
            subprocess.check_call(
                f"pip install --platform manylinux2014_x86_64 --target={output_dir}/python/ --python-version 3.12 --only-binary=:all: --upgrade pymupdf".split()
            )


        dependency_layer = _lambda.LayerVersion(
            self,
            f"{self.stack_name}-dependencies",
            code=_lambda.Code.from_asset(output_dir),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Dependencies Layer",
            removal_policy=RemovalPolicy.DESTROY,
        )

        generator_function = _lambda.Function(
            self,
            "lectionary_pdf_generator_fn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset('./lambda'),
            handler='lectionary_function.lambda_handler',
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "SENDER_EMAIL": ssm.StringParameter.value_for_string_parameter(
                    self, "sender_email"
                ),
                "RECIPIENT_EMAIL": ssm.StringParameter.value_for_string_parameter(
                    self, "recipient_email"
                ),
            },
            layers=[dependency_layer],
        )

        generator_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=['SES:SendRawEmail'],
                resources=['*'],
                effect=iam.Effect.ALLOW,
            )
        )

        # Run every Monday at 12pm UTC
        rule = events.Rule(
            self, 
            "pdf-generator-eventrule",
            schedule = events.Schedule.cron(
                hour="12",
                minute="0",
                month="*",
                week_day="MON",
                year="*"
            )
        )
        rule.add_target(targets.LambdaFunction(generator_function))
