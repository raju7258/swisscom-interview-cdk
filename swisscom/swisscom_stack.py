from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_signer as signer,
    aws_lambda as _lambda,
    custom_resources as cr,
    CustomResource
)
from aws_cdk.lambda_layer_kubectl_v34 import KubectlV34Layer
from constructs import Construct
import os 
from aws_cdk import Token

class SwisscomStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, *, vpc: ec2.IVpc = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Fetch AWS Account number from Context.json file
        aws_account_id = self.node.try_get_context("aws-account-id")

        # EKS cluster
        cluster = eks.Cluster(self, "MyEKS",
                    version=eks.KubernetesVersion.V1_34,
                    endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,
                    default_capacity=0,
                    default_capacity_instance=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
                    kubectl_layer=KubectlV34Layer(self, "kubectl"),
                    vpc=vpc,
                    vpc_subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)],
                    cluster_name="MyEKS",
                    tags={"Name": "MyEKS", "Purpose": "Swisscom-Interview"}
                    )
        # Adding current User 
        admin_user = iam.User(self, "EKSAdmin")
        cluster.aws_auth.add_user_mapping(admin_user, groups=["system:masters"])
        
        # IAM Policy
        myeksmgmtpolicy = iam.Policy(self, "MyEKSMgmtPolicy", 
                                     statements=[
                                         iam.PolicyStatement(
                                             actions=[
                                                 "eks:Describe*",
                                                 "eks:List*",
                                                 "eks:AccessKubernetesApi",
                                                ],
                                             resources=["*"]
                                         )
                                     ]
                                    )
        
        # IAM Role created for EKS Admin tasks
        MyEKSMgmtRole = iam.Role(self, "MyEKSMgmtRole", assumed_by=iam.ArnPrincipal(f"arn:aws:iam::{aws_account_id}:user/cdk-usr"), role_name="MyEKSMgmtRole")

        # Attaching IAM Policy to Role
        myeksmgmtpolicy.attach_to_role(MyEKSMgmtRole)

        # Add role to system:masters
        cluster.aws_auth.add_masters_role(MyEKSMgmtRole)

        # Create SSM Parameter to store environment as value
        ssm.StringParameter(self, "MyEnvParam",
                                string_value="development",
                                description="Environment Name",
                                parameter_name="/platform/account/env"
                               )        

        # Create an AWS Lambda function to fetch environment details from SSM 
        signing_profile = signer.SigningProfile(self, "SigningProfile",
                                platform=signer.Platform.AWS_LAMBDA_SHA384_ECDSA
                            )
        
        # Create a code signing config
        code_signing_config = _lambda.CodeSigningConfig(self, "CodeSigningConfig",
                                    signing_profiles=[signing_profile]
                                )
        
        # Create Lambda Function
        fn = _lambda.Function(self, "MySSMParamLambda",
                        runtime=_lambda.Runtime.PYTHON_3_13,
                        handler="index.lambda_handler",
                        code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), "lambda_functions")),
                        environment={
                            "SSM_PARAM_NAME": "/platform/account/env"
                        },
                        code_signing_config=code_signing_config,
                        )
        # Additional policy for Lambda Execution Role
        fn.add_to_role_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter/platform/account/env"]
        ))

        # CustomResource Provider 
        provider = cr.Provider(self, "EnvToHelmProvider",
                    on_event_handler=fn,
                    )
        
        env_cr = CustomResource(self, "EnvToHelmValues", service_token=provider.service_token)

        replica_count = Token.as_number(env_cr.get_att("ReplicaCount"))

        # Add NGINX Ingress Controller to EKS
        nginx_ingress = cluster.add_helm_chart("nginx-ingress", chart="nginx-ingress", repository="https://helm.nginx.com/stable", namespace="kube-system", values={"controller": { "replicaCount": replica_count }})

