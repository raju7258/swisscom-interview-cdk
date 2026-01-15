from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
)

from constructs import Construct

class NetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(self, "SwisscomVPC", 
                           max_azs=2, nat_gateways=1, 
                           subnet_configuration=[
                               ec2.SubnetConfiguration(name="mypublicsub", subnet_type=ec2.SubnetType.PUBLIC), 
                               ec2.SubnetConfiguration(name="myprivatesub", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
                            ]
                    )
