from aws_cdk import (
    aws_lambda as _lambda,
    Duration,
    Stack,
)
from constructs import Construct

class LectionaryPdfGeneratorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        generator_function = _lambda.Function(
            self,
            "lectionary_pdf_generator_fn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset('./lambda'),
            handler='lectionary_function.lambda_handler',
            timeout=Duration.seconds(30),
        )
