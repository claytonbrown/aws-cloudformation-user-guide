#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Summary.

"""

from collections import OrderedDict
from os.path import expanduser
from tempfile import mktemp
from urllib.request import urlretrieve
from zipfile import ZipFile
import markdownify
import argparse
import cfn_constructors
import collections
import gzip
import inflection
import io
import json
import logging
import os
import requests
import requests_cache
import ruamel.yaml
import shlex
import subprocess
import sys
import traceback
from datetime import date, datetime


log = logging.getLogger(__name__)
# log.setLevel(logging.INFO)
module_path = os.path.dirname(__file__)
requests_cache.install_cache('requests_cache', backend='sqlite', expire_after=3000000)

cfrs_spec_file = "aws_service_info/CloudFormationResourceSpecification.json"
cfn_decorations_file = "aws_service_info/cfn_decorate_rules.json"
cf_resources_by_region_file = "aws_service_info/aws-cloudformation-resources-by-region.json"
aws_product_descriptions_file = "aws_service_info/aws-product-descriptions.json"

# source urls
URL_CFN_RESOURCE_SPECIFICATIONS = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html"
URL_CFN_RESOURCE_TYPES = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html"
URL_AWS_REGIONS_AND_ENDPOINTS = "https://docs.aws.amazon.com/general/latest/gr/rande.html"
URL_REGIONAL_PRODUCT_SERVICES = "https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/"
URL_AWS_PRODUCTS_URL = "https://aws.amazon.com/products/"
URL_AWS_RELEASE_NOTES = "https://aws.amazon.com/releasenotes/"
URL_AWS_COMPLIANCE_SCOPE = "https://aws.amazon.com/compliance/services-in-scope/"
URL_AWS_CLOUDTRAIL_SUPPORT = "https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-supported-services.html"
URL_AWS_CFN_SUPPORTED_RESOURCES = "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-supported-resources.html"
URL_IAM_SERVICE_NAMES = "https://raw.githubusercontent.com/widdix/complete-aws-iam-reference/master/tools/serviceNames.json"
URL_EC2_INSTANCE_INFO = "https://raw.githubusercontent.com/powdahound/ec2instances.info/master/www/instances.json"
# output files
FILE_AWS_CLOUDFORMATION_RESOURCES_BY_REGION = "aws_service_info/aws-cloudformation-resources-by-region.json"
FILE_AWS_CLOUFORMATION_PRODUCTS_BY_REGION = "aws_service_info/aws-clouformation-products-by-region.json"
FILE_REFERENCE_AWS_PRODUCT_DESCRIPTIONS = "aws_service_info/aws-product-descriptions.json"
FILE_CFRS_SCHEMAS = "aws_service_info/aws-cfrs-schemas.json"
FILE_CFRS_SUMMARY = "aws_service_info/aws-cfrs-summary.json"
FILE_CFRS_DEFAULTS = "aws_service_info/aws-cfrs-defaults.json"
FILE_BEST_PRACTICES = "aws_service_info/aws-service-best-practices.json"
FILE_REFERENCE_AWS_PRODUCT_COMPLIANCE = "aws_service_info/aws-product-compliance.json"
FILE_REFERENCE_PRODUCT_REGION_ENDPOINTS = "aws_service_info/aws-product-region-endpoints.json"
FILE_REFERENCE_AWS_REGIONNAMES_TO_APINAMES = "aws_service_info/aws-regionnames-to-apinames.json"
FILE_REFERENCE_AWS_REGIONS = "aws_service_info/aws-regions.json"
FILE_REFERENCE_AWS_REGIONAL_PRODUCTS = "aws_service_info/aws-regional-product-services.json"
FILE_REFERENCE_CFN_DECORATE_RULES = "aws_service_info/cfn_decorate_rules.json"
FILE_REFERENCE_EC2_INSTANCES = "aws_service_info/ec2_instances.latest.json"
FILE_REFERENCE_IAM_ACTIONS = "aws_service_info/iam-actions.json"
FILE_REFERENCE_IAM_COMPLETIONS = "aws_service_info/iam-completions.json"

MAX_CFN_TEMPLATE_SIZE = 460800  # Bytes

JSON_WITH_COMMENTS = True

if JSON_WITH_COMMENTS:
    # import commentjson as json
    # import json as original_json
    from jsoncomment import JsonComment
    json = JsonComment(json)


config = {}

# "$schema": "https://raw.githubusercontent.com/claytonbrown/goformation/master/schema/cloudformation.schema.json",

basetemplate = """
{
    "AWSTemplateFormatVersion" : "2010-09-09",
    "Description" : "Base Template",
    "Metadata": {},
    "Parameters": {},
    "Mappings": {},
    "Conditions": {},
    "Transform": {},
    "Resources": {},
    "Outputs": {}
}
"""


sort_order = ['AWSTemplateFormatVersion',
              'Description',
              'Metadata',
              'Parameters',
              'Rules',
              'Mappings',
              'Conditions',
              'Transform',
              'Resources',
              'Outputs'
              ]

tagging_standards = [
    {"Key": "app_version", "Value": {"Ref": "TagsAppVersion"}},
    {"Key": "compliance", "Value": {"Ref": "TagsCompliance"}},
    {"Key": "confidentiality", "Value": {"Ref": "TagsConfidentiality"}},
    {"Key": "cost_code", "Value": {"Ref": "TagsCostCode"}},
    {"Key": "cost_owner", "Value": {"Ref": "TagsOwner"}},
    {"Key": "environment", "Value": {"Ref": "TagsEnvironment"}},
    {"Key": "kms_encryption_key", "Value": {"Ref": "TagsKMSKeyArn"}},
    {"Key": "logging_bucket", "Value": {"Ref": "TagsLoggingBucket"}},
    {"Key": "owner_email", "Value": {"Ref": "TagsOwnerEmail"}}
]

tpl = """\
{{#x}}
 - {{k}}: {{v}}
{{/x}}"""


aws_product_region_endpoints = None
aws_product_compliance_info = None

iam_resources = ['AWS::IAM::Role']

cfn_known_stubs = set(["appsync", "cloudformation", "opsworks", "iot", "wafregional", "logs", "redshift", "stepfunctions", "waf", "ec2", "ses", "lambda", "iam", "config", "cloudfront", "autoscaling", "glue", "inspector", "dms", "dynamodb", "apigateway", "elasticsearch", "elasticache", "ssm", "codepipeline", "cognito", "gamelift", "applicationautoscaling", "elasticloadbalancingv2", "serverless transform", "cloudwatch", "codedeploy", "sns", "codebuild", "emr", "include transform", "sqs", "ecs", "rds", "efs", "servicediscovery", "guardduty", "events", "kms", "elasticloadbalancing", "kinesisanalytics", "dax", "kinesis", "certificatemanager", "batch", "sdb", "route53", "kinesisfirehose", "elasticbeanstalk", "directoryservice", "cloud9", "s3", "codecommit", "ecr", "cloudtrail", "workspaces", "athena", "datapipeline"])

# not linked to from /products website
product_descriptions = {
    "sdb": {
        "alias": "sdb",
        "name": "AWS Simple DB",
        "description": "Amazon SimpleDB is a highly available NoSQL data store that offloads the work of database administration.",
        "url": "https://aws.amazon.com/simpledb/",
    },
    "dax": {
        "alias": "dax",
        "name": "AWS DynamoDB Accelerator (DAX)",
        "description": "AWS DynamoDB Accelerator (DAX)",
        "url": "https://aws.amazon.com/dynamodb/dax/",
    },
    "kinesisfirehose": {
        "alias": "kinesisfirehose",
        "name": "Amazon Kinesis Data Firehose",
        "description": "Amazon Kinesis Data Firehose is the easiest way to load streaming data into data stores and analytics tools.",
        "url": "https://aws.amazon.com/kinesis/data-firehose/",
    },
    "kinesisanalytics": {
        "alias": "kinesisanalytics",
        "name": "Amazon Kinesis Data Analytics",
        "description": "Get actionable insights from streaming data in real-time.",
        "url": "https://aws.amazon.com/kinesis/data-analytics/",
    },
    "elb": {
        "alias": "elb",
        "name": "Elastic Load Balancer (ELB)",
        "description": "Classic Load Balancer provides basic load balancing across multiple Amazon EC2 instances and operates at both the request level and connection level.",
        "url": "https://aws.amazon.com/elasticloadbalancing/",
    },
    "alb": {
        "alias": "alb",
        "name": "Application Load Balancer (ALB)",
        "description": "Application Load Balancer operates at the request level (layer 7), routing traffic to targets - EC2 instances, containers and IP addresses based on the content of the request.",
        "url": "https://aws.amazon.com/elasticloadbalancing/",
    },
    "nlb": {
        "alias": "nlb",
        "name": "Network Load Balancer (NLB)",
        "description": "Network Load Balancer operates at the connection level (Layer 4), routing connections to targets - Amazon EC2 instances, containers and IP addresses based on IP protocol data.",
        "url": "https://aws.amazon.com/elasticloadbalancing/",
    }
}

# products not linkable to cfn resource names
unmatched_cfn_services = {
    "servicediscovery": ["route53"],
    "events": ["cloudwatch"],
    "ssm": ["systemsmanager"],
    "elasticloadbalancing": ["elb"],
    "applicationautoscaling": ["autoscaling"],
    "wafregional": ["waf"],
    "elasticloadbalancingv2": ["alb", "nlb"],
    "logs": ["cloudwatch"]
}


cloudformation_arn_additional_resource_mappings = {
    "cloudwatch": ["logs", "events"],
    "dynamodb": ["dax"],
    "ec2": ["ebs"],
    "elasticloadbalancing": ["elasticloadbalancingv2"],
    "kinesis": ["kinesisfirehose", "kinesisanalytics"],
    "waf": ["wafregional"]
    # "iot": [""],
}

# TODO: pip install nested-lookup
# https://github.com/russellballestrini/nested-lookup/


class ObjectEncoder(json.JSONEncoder):
    def default(self, obj):

        if hasattr(obj, "to_json"):
            return self.default(obj.to_json())

        elif isinstance(obj, (CommentedMap)):
            return obj[0]

        elif isinstance(obj, (datetime, date)):
            return obj.isoformat().split("T")[0]

        elif hasattr(obj, "__dict__"):
            d = dict(
                (key, value)
                for key, value in inspect.getmembers(obj)
                if not key.startswith("__")
                and not inspect.isabstract(value)
                and not inspect.isbuiltin(value)
                and not inspect.isfunction(value)
                and not inspect.isgenerator(value)
                and not inspect.isgeneratorfunction(value)
                and not inspect.ismethod(value)
                and not inspect.ismethoddescriptor(value)
                and not inspect.isroutine(value)
            )
            return self.default(d)
        return obj


def json_serialize_datetimes(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat().split("T")[0]
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    # log.warning(obj)
    raise TypeError("Type %s not serializable" % type(obj))


def find_nested_keys_value(key, dictionary):
    for k, v in dictionary.iteritems():
        if k == key:
            yield v
        elif isinstance(v, dict):
            for result in find_nested_keys_value(key, v):
                yield result
        elif isinstance(v, list):
            for d in v:
                for result in find_nested_keys_value(key, d):
                    yield result


def get_additional_cloudformation_arns(arn):
    """Summary

    Args:
        arn (TYPE): Description

    Returns:
        TYPE: Description
    """
    if "::" in arn:
        arn = arn.lower().split("::")[1]

    arns = [arn]
    if arn in cloudformation_arn_additional_resource_mappings:
        for new_arn in cloudformation_arn_additional_resource_mappings[arn]:
            arns.append(new_arn)
    return arns


endpoint_service_mapping = {
    "api": "pricing",
    "acm": "certificatemanager",
    "cloudhsmv2": "cloudhsmv2",
    "events": "cloudwatch",
    "logs": "cloudwatch",
    "dynamodbstreams": "dynamodb",
    "glacier": "glacier1",
    "kinesisanalytics": "kinesisanalytics",
    "firehose": "kinesisfirehose",
    "wafregional": "waf"
}

cf_resource_type_sub_products_mappings = {
    "vpc": "ec2",
    "wafregional": "waf",
    "rdsaurora": "rds",
    "glacier1": "s3",
    "wafregional": "waf",
    "applicationautoscaling": "ec2",
    "autoscaling": "ec2",

    # "EC2::Volume": "ec2",
    "events": "cloudwatch"
    # "EC2::VPN", "ec2"

}

cf_cloudformation_arn_to_service_name__mappings = {
    "emr": "elasticmapreduce",
    "ssm": "systemsmanager",
    "iot": "iotcore",
    "logs": "cloudwatch",
    "events": "cloudwatch",
    "cloudwatchlogs": "cloudwatch"

}


def map_cfn_arn_to_service_name(stub):
    """Summary

    Args:
        stub (TYPE): Description

    Returns:
        TYPE: Description
    """
    service_name = stub
    if "::" in stub:
        service_name = stub.lower().split("::")[1]

    if stub in cf_cloudformation_arn_to_service_name__mappings:
        service_name = cf_cloudformation_arn_to_service_name__mappings[stub]
        log.info("Translating service stub: %s to service_name: %s" % (stub, service_name))
    return service_name


cf_service_name_cloudformation_arn_mappings = {
    "dynamodbdax": "dax",
    "elasticmapreduce": "emr",
    "simpledb": "sdb",
    "elasticsearchservice": "elasticsearch",
    "ec2systemsmanager": "ssm",
    "applicationautoscaling": "autoscaling",
    "alb": "elasticloadbalancingv2",
    "applicationloadbalancer": "elasticloadbalancingv2",
    "networkloadbalancer": "elasticloadbalancingv2",
    "nlb": "elasticloadbalancingv2",
    "glacier1": "s3",
    "glacier": "s3",
    "vpc": "ec2",
    # "ebs": "EC2::Volume",
    "rdsaurora": "rds"
    # "todo4": "kinesisanalytics",
    # "todo4": "kinesisfirehose",
    # "todo4": "wafregional"
    # "directconnect", ""
    # "vpn": "EC2::VPN"
}


def map_service_stub_to_cloudformation_arn(service_stub):
    if service_stub in cf_service_name_cloudformation_arn_mappings:
        return cf_service_name_cloudformation_arn_mappings[service_stub]
    else:
        return service_stub


def map_compliance_name_to_endpoint_stub(service_name):
    """Summary

    Args:
        stub (TYPE): Description

    Returns:
        TYPE: Description
    """
    compliance_endpoint_mappings = {
        "simpledb": "sdb",

    }
    if stub in compliance_endpoint_mappings:
        log.warn("Mapping compliance name [%s] to endpoint stub [%s]" % (service_name, compliance_endpoint_mappings[service_name]))
        return compliance_endpoint_mappings[service_name]
    else:
        return service_name


def map_endpoint_stub_to_cf_name(stub):
    """Summary

    Args:
        stub (TYPE): Description

    Returns:
        TYPE: Description
    """
    endpoint_resource_mappings = {
        "api": "pricing",
        "acm": "certificatemanager",
        "a4b": "alexaforbusiness",
        "autodiscoverservice": "workmail",
        "cognitoidentity": "cognito",
        "cognitoidp": "cognito",
        "cognitosync": "cognito",
        "ds": "directoryservice",
        "elasticbeanstalkhealth": "elasticbeanstalk",
        "elasticfilesystem": "efs",
        "elasticmapreduce": "emr",
        "emailsmtp": "ses",
        "emr": "emr",
        "es": "elasticsearch",
        "events": "cloudwatch",
        "ews": "workmail",
        "firehose": "kinesisfirehose",
        "imap": "workmail",
        "inboundsmtp": "ses",
        "inspector": "inspector",
        "logs": "cloudwatch",
        "models": "lex",
        "monitoring": "cloudwatch",
        "mgh": "migrationhub",
        "mturkrequester": "mechanicalturk",
        "mturkrequestersandbox": "mechanicalturk",
        "mobile": "workmail",
        "opsworkscm": "opsworks",
        "outlook": "workmail",
        "queue": "sqs",
        "route53domains": "route53",
        "runtime": "lex",
        "s3apnortheast1": "s3",
        "s3apnortheast2": "s3",
        "s3apsouth1": "s3",
        "s3apsoutheast1": "s3",
        "s3apsoutheast2": "s3",
        "s3cacentral1": "s3",
        "s3eucentral1": "s3",
        "s3euwest1": "s3",
        "s3euwest2": "s3",
        "s3euwest3": "s3",
        "s3external1": "s3",
        "s3saeast1": "s3",
        "s3useast2": "s3",
        "s3uswest1": "s3",
        "s3uswest2": "s3",
        "s3website": "s3",
        "s3websiteapnortheast1": "s3",
        "s3websiteapsoutheast1": "s3",
        "s3websiteapsoutheast2": "s3",
        "s3websiteeuwest1": "s3",
        "s3websitesaeast1": "s3",
        "s3websiteuseast1": "s3",
        "s3websiteuswest1": "s3",
        "s3websiteuswest2": "s3",
        "simpledb": "sdb",
        "sms": "servermigrationservice",
        "smtp": "workmail",
        "states": "stepfunctions",
        "streams": "dynamodbstreams",
        "sts": "simpletokenservice",
        "swf": "simpleworkflow",
    }
    if stub in endpoint_resource_mappings:
        log.debug("Mapping endpoint [%s] to CFN arn [%s]" % (stub, endpoint_resource_mappings[stub]))
        return endpoint_resource_mappings[stub]
    else:
        return stub


def aws_parametize_name(name):
    return inflection.parameterize(normalize_service_name(name).split("(")[0]).replace('-', '-')


def normalize_service_name(name):
    return name.lower().replace('aws ', '').replace('amazon ', '').replace('/', ' ').replace('\n', ' ').replace('  ', ' ')
    # .replace(" & "," and")


def normalize_search_terms(name):
    """Summary

    Args:
        name (TYPE): Description

    Returns:
        TYPE: Description
    """
    search_terms = set()

    name = normalize_service_name(name)

    name_incl_brackets = ''.join([i for i in name if i.isalpha()])
    search_terms.add(name_incl_brackets.lower())

    tla_guess = ''.join([c for c in inflection.titleize(name.split('(')[0]) if c.isupper()]).lower().replace(" ", "")
    search_terms.add(tla_guess)

    name = name.lower()

    #  detect TLA in brackets
    try:
        tla = name.split('(')[1].split(')')[0].lower().replace(" ", "")
        search_terms.add(tla)
    except Exception:
        pass

    name = name.split('(')[0]
    search_terms.add(name.replace(" ", ""))
    search_terms.add(name.split('(')[0].lower().replace(" ", ""))
    service_name_search_string = name.split('(')[0].lower().strip().replace(" ", "").replace("-", "")
    if service_name_search_string in cf_service_name_cloudformation_arn_mappings:
        # remap to cloudformation arn based names if detected
        new_search_string = cf_service_name_cloudformation_arn_mappings[service_name_search_string]
        log.debug("Coercing name from %s to %s" % (service_name_search_string, new_search_string))
        search_terms.add(new_search_string)
    else:
        search_terms.add(service_name_search_string)

    # boot any strings < 3 chars long
    search_term_results = []
    for term in search_terms:
        if len(term) > 1:
            search_term_results.append(term)

    log.debug("Normalized %s to %s" % (name, search_terms))
    return search_term_results


def filter_resources(filter_word, resources_list):
    """Summary

    Args:
        filter_word (TYPE): Description
        resources_list (TYPE): Description

    Returns:
        TYPE: Description
    """
    log.info("Filter resources by %s" % (filter_word))
    filtered_resources = []
    for resource_name in resources_list:
        log.debug("Resource: %s" % (resource_name))
        if filter_word.lower() in resource_name.lower():
            filtered_resources.append(resource_name)
    return filtered_resources


def aws_arn_normalizer(name):
    """Summary

    Args:
        name (TYPE): Description

    Returns:
        TYPE: Description
    """
    service_name_search_string = name.split('(')[0].lower().strip().replace(" ", "").replace("-", "")
    service_name_search_string = service_name_search_string.lstrip("amazon")
    service_name_search_string = service_name_search_string.lstrip("aws")
    if service_name_search_string in cf_service_name_cloudformation_arn_mappings:
        # remap to cloudformation arn based names if detected
        new_search_string = cf_service_name_cloudformation_arn_mappings[service_name_search_string]
        log.info("Coercing name from %s to %s" % (service_name_search_string, new_search_string))
        return new_search_string
    else:
        return service_name_search_string

def load_cfn_resources_by_region(json_file=FILE_AWS_CLOUDFORMATION_RESOURCES_BY_REGION):
    # reference/aws-cloudformation-resources-by-region.json
    cf_resources_by_region_data = None
    with open(json_file, 'r') as cfresources:
        cf_resources_by_region_data = json.load(cfresources)
        log.warn("Loading %s" % (json_file))
    return cf_resources_by_region_data


def load_iam_scrape_data(json_file=FILE_REFERENCE_IAM_ACTIONS):
    #  "reference/iam-actions.json"
    iam_data = {}
    with open(json_file, 'r') as iamresources:
        iam_data = json.load(iamresources)
        log.warn("Loading %s" % (json_file))
    return iam_data

def load_product_compliance(json_file=FILE_REFERENCE_AWS_PRODUCT_COMPLIANCE):
    #  "reference/iam-actions.json"
    compliance_data = {}
    with open(json_file, 'r') as file_handle:
        compliance_data = json.load(file_handle)
        log.warn("Loading %s" % (json_file))
    return compliance_data

def load_product_descriptions(json_file=FILE_REFERENCE_AWS_PRODUCT_DESCRIPTIONS):
    #  "reference/aws-product-descriptions.json"
    data = {}
    with open(json_file, 'r') as file_handle:
        data = json.load(file_handle)
        log.warn("Loading %s" % (json_file))
    return data

FILE_REFERENCE_AWS_PRODUCT_DESCRIPTIONS

def log_data(data, log_level=log.debug):
    """Summary

    Args:
        data (TYPE): Description
        log_level (TYPE, optional): Description
    """
    log_level(json.dumps(data, indent=4, sort_keys=True))


def service_link_to_normalized_name(link):
    """Summary

    Args:
        link (TYPE): Description

    Returns:
        TYPE: Description
    """
    if "https://aws.amazon.com" in link:
        link = link.lower().replace("https://aws.amazon.com", "")
    elif "https://docs.amazon.com" in link:
        link = link.lower().replace("https://docs.amazon.com", "")
    if "#" in link:
        name = link.lower().split('#')[-1].replace('-', '')
    else:
        name = link.lower().strip('/').replace('/', '-').split('-?')[0].replace("http:--", "").replace("https:--", "").split(".")[0].replace("-", "")

    # name = name.replace("amazon","").replace("aws","")
    # return normalize_search_terms(name)
    log.debug("ProductUrl [%s] : %s" % (name, link))
    return name


def scrape_cfn_property_docs(docsUrl):

    log.info("Scraping service advice: %s" % (docsUrl))

    if '#' not in docsUrl:
        return ''
    else:
        try:
            anchor = docsUrl.split('#')[-1]
            log.warning(anchor)
            data = urlopen(docsUrl)

            #TODO make this unhacky HACK HACK HACK
            data = data.read().split(anchor)[1].split('</a>')[1]
            #.split('</dd>')[0]
            log.warning(data)


            return markdownify.markdownify(data)
        except Exception as e:
            log.warning(e)

def urlopen(theurl):
    """Summary

    Args:
        theurl (TYPE): Description

    Returns:
        TYPE: Description
    """
    return io.StringIO(scrape_url(theurl))


def scrape_url(theurl):
    """Summary

    Args:
        theurl (TYPE): Description

    Returns:
        TYPE: Description
    """
    log.debug("Scrape [%s]" % (theurl))
    r = requests.get(theurl)
    return r.text


def download(theurl, target_filename=None):
    """Summary.

    Args:
        theurl (TYPE): Description
        target_filename (TYPE): Description

    Returns:
        TYPE: Description
    """
    response = None
    log.debug("Download [%s] -> %s" % (theurl, target_filename))
    try:
        r = requests.get(theurl, headers={"Accept-Encoding": "gzip"}, stream=True)
        log.debug("Response code: %s" % (r.status_code))
        log.debug(r.headers)

        if r.headers['Content-Encoding'] == 'gzip':
            try:
                handle = io.BytesIO()
                for chunk in response.iter_content(chunk_size=512):
                    if chunk:  # filter out keep-alive new chunks
                        handle.write(chunk)
                compressed_data = gzip.GzipFile(fileobj=handle)
                response = compressed_data.read()
                log.debug("Gzipped compressed file downloaded/extracted")
            except Exception as e:
                log.debug(e)
                log.debug("Response is gzip compressed")
                # response = r.content
                response = r.text
        else:
            log.info("Response is NOT gzip compressed")
            response = r.text

        if target_filename is not None:
            with open(target_filename, 'w') as output:
                if target_filename.lower().endswith(".json"):
                    log.debug("Loading json response into data")
                    response = json.loads(response)
                    output.write(json.dumps(response, indent=4, sort_keys=True))
                else:
                    output.write(response)
                log.info("Written: %s" % (target_filename))

        return response
    except Exception as e:
        print(e)
        log_traceback(log, e)
        log.warn(e)


def download_zip_and_extract(theurl, dest_dir):
    """Summary.

    Args:
        theurl (TYPE): Description
        dest_dir (TYPE): Description
    """
    try:
        filename = mktemp('.zip')
        # dest_dir = mktemp()
        urlretrieve(theurl, filename)
        # download(theurl, filename)
        thefile = ZipFile(filename)
        thefile.extractall(dest_dir)
        thefile.close()
        log.info("Finished extracting %s to : %s" % (theurl, dest_dir))
        print("Finished extracting %s to : %s" % (theurl, dest_dir))
    except Exception as e:
        print(e)
        log.warn(e)


def load_json(filename):
    """Summary.

    Args:
        filename (TYPE): Description

    Returns:
        TYPE: Description
    """
    with open(filename, 'r') as f:
        try:
            log.info("Loading JSON file: %s" % (filename))
            return json.load(f)
        except Exception as e:
            log.warn("Could not load JSON file: %s" % (filename))
            log.debug(e)
            return {}


def extract_servicename_from_endpoint(endpoint):
    """Summary

    Args:
        endpoint (TYPE): Description

    Returns:
        TYPE: Description
    """
    servicename = endpoint.lower().replace('https://', '')  # replace("<unique-id>", "").replace("prefix.", "")
    splitname = servicename.strip('.').split('.')

    ignore_subdomains = list(aws_product_region_endpoints["region_labels"].keys())
    ignore_subdomains.append("prefix")
    ignore_subdomains.append("<unique-id>")

    known_endpoints = list(aws_product_compliance_info["services"].keys())
    known_products = list(aws_product_region_endpoints["services"].keys())

    # check if regional subdomain
    # print(endpoint)
    # print(splitname)
    servicename = splitname[0]
    # print(splitname)
    # print(ignore_subdomains)
    # print(splitname[0] in aws_product_region_endpoints["region_labels"])

    # print(aws_product_region_endpoints["region_labels"])
    if servicename in ignore_subdomains:
        # first subdomain is a regional api name
        servicename = splitname[1]
    # print(servicename)
    servicename = servicename.replace('-', '')
    # print(servicename)
    mapped_service_name = map_endpoint_stub_to_cf_name(servicename)

    if mapped_service_name in known_endpoints:
        log.debug("Mapped service [%s] name found in aws_product_compliance_info" % (mapped_service_name))
        return mapped_service_name
    if mapped_service_name in known_products:
        log.debug("Mapped service [%s] name found in aws_product_region_endpoints" % (mapped_service_name))
        return mapped_service_name

    log.debug("Mapped service [%s] name not found in aws_product_compliance_info or aws_product_region_endpoints" % (mapped_service_name))
    return "unknown"


class SortedListEncoder(json.JSONEncoder):

    """Summary
    """

    def encode(self, obj):
        """Summary

        Args:
            obj (TYPE): Description

        Returns:
            TYPE: Description
        """
        def sort_lists(item):
            """Summary

            Args:
                item (TYPE): Description

            Returns:
                TYPE: Description
            """
            if isinstance(item, list):
                return sorted(sort_lists(i) for i in item)
            elif isinstance(item, dict):
                return {k: sort_lists(v) for k, v in item.items()}
            else:
                return item
        return super(SortedListEncoder, self).encode(sort_lists(obj))


def flattenDict(d, result=None):
    """
    A class that collapses nested dictionaries into single 2D flat dot notation HashMap / Dictionary

    Does it handles result with value None passed?
    >>> import utils
    >>> result = utils.flattenDict( {}, result=None )
    >>> type(result) == type({})
    True


    >>> result = utils.flattenDict( {"a": {"b":{"c":"literalvalue"}}})

    >>> 'a.b.c' in result
    True

    >>> result['a.b.c'] == "literalvalue"
    True

    result = utils.flattenDict( {"a": {"b":{"c":[{"d1":"foo"},{"d2","bar"}]}}})
    import pprint
    pprint.pprint(result)
    result["a.b.c.d1"] == "foo"
    True
    result["a.b.c.d2"] == "bar"
    True


    >>> result = utils.flattenDict( {"a": {"b":{"c":["my","array"]}}})
    >>> "a.b.c" in result
    True

    """
    if result is None:
        result = {}
    for key in d:
        value = d[key]
        if isinstance(value, dict):
            value1 = {}
            for keyIn in value:
                value1[".".join([key, keyIn])] = value[keyIn]
            flattenDict(value1, result)
        elif isinstance(value, (list, tuple)):
            for indexB, element in enumerate(value):
                if isinstance(element, dict):
                    value1 = {}
                    index = 0
                    for keyIn in element:
                        # newkey = ".".join([key, keyIn])
                        value1[".".join([key, keyIn])] = value[indexB][keyIn]
                        index += 1
                    for keyA in value1:
                        flattenDict(value1, result)
        else:
            result[key] = value
    return result


# TODO incorporate into CF propreties sort order
def make_custom_sort(orders):
    """
    Sort in a specified order any dictionary nested in a complex structure.
    Especially useful for sorting a JSON file in a meaningful order.

    Args:
        orders: a list of lists of keys in the desired order.

    Returns:
        A new object with any nested dict sorted accordingly.
        See test-customsort.py for more details and edge cases.

    Example:
        >>> stuff = {
        ...     "Alice": 0,
        ...     "Bob": [1, 2, {"fizz": 4, "buzz": 6, "fizzbuzz": 7}],
        ...     "Eve": set("ABC"),
        ...     "Oscar": {"fizz": 3, "buzz": 5, "fizzbuzz": 15}
        ... }
        >>> custom_sort = make_custom_sort([["Oscar","Alice","Bob","Eve"], ["buzz","fizzbuzz","fizz"]])
        >>> sorted_stuff = custom_sort(stuff)
        >>> assert sorted_stuff == OrderedDict([
        ...     ('Oscar', OrderedDict([('buzz', 5), ('fizzbuzz', 15), ('fizz', 3)])),
        ...     ('Alice', 0),
        ...     ('Bob', [1, 2, OrderedDict([('buzz', 6), ('fizzbuzz', 7), ('fizz', 4)])]),
        ...     ('Eve', set(['A', 'C', 'B']))
        ... ])
    """
    orders = [{k: -i for (i, k) in enumerate(reversed(order), 1)} for order in orders]

    def process(stuff):
        """Summary

        Args:
            stuff (TYPE): Description

        Returns:
            TYPE: Description
        """
        if isinstance(stuff, dict):
            l = [(k, process(v)) for (k, v) in stuff.iteritems()]
            keys = set(stuff)
            for order in orders:
                if keys.issubset(order) or keys.issuperset(order):
                    return OrderedDict(sorted(l, key=lambda x: order.get(x[0], 0)))
            return OrderedDict(sorted(l))
        if isinstance(stuff, list):
            return [process(x) for x in stuff]
        return stuff
    return process


class Singleton(type):

    """Summary.
    """

    _instances = {}

    def __call__(self, *args, **kwargs):
        """Summary.

        Args:
            *args: Description
            **kwargs: Description

        Returns:
            TYPE: Description
        """
        if self not in self._instances.keys():
            self._instances[self] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]


class LoggerManager(object):

    """Summary.
    """

    __metaclass__ = Singleton

    _loggers = {}

    def __init__(self, *args, **kwargs):
        """Summary.

        Args:
            *args: Description
            **kwargs: Description
        """
        pass

    @staticmethod
    def getLogger(name=None):
        """Summary.

        Args:
            name (None, optional): Description

        Returns:
            TYPE: Description
        """
        if not name:
            logging.basicConfig()
            return logging.getLogger()
        elif name not in LoggerManager._loggers.keys():
            logging.basicConfig()
            LoggerManager._loggers[name] = logging.getLogger(str(name))
        return LoggerManager._loggers[name]


def log_traceback(exception_logger, ex, ex_traceback=None):
    """Summary

    Args:
        exception_logger (TYPE): Description
        ex (TYPE): Description
        ex_traceback (None, optional): Description
    """
    if ex_traceback is None:
        ex_traceback = ex.__traceback__
    tb_lines = [line.rstrip('\n') for line in
                traceback.format_exception(ex.__class__, ex, ex_traceback)]
    exception_logger.warn(tb_lines)


"""
def load_config(file_name):
    "Summary.

    Args:
        file_name (TYPE): Description
    "
    config = None
    if not os.path.isfile(file_name):
        log.warn("Config file not found: %s" % (file_name))
    else:
        try:
            log.info("Loading config: %s" % (file_name))
            config = ruamel.yaml.load(file_name)
            log_data(config, log.info)
        except Exception as e:
            log.warn(e)
    return config
"""


def run_command(command_line):
    """Summary.

    Args:
        command_line (TYPE): Description

    Returns:
        TYPE: Description

    Deleted Parameters:
        cmd (TYPE): Description
    """
    output = ""
    log.info(command_line)
    process = subprocess.Popen(shlex.split(command_line), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    return output


def make_custom_sort(orders):
    orders = [{k: -i for (i, k) in enumerate(reversed(order), 1)} for order in orders]

    def process(stuff):
        if isinstance(stuff, dict):
            l = [(k, process(v)) for (k, v) in stuff.items()]
            keys = set(stuff)
            for order in orders:
                if keys.issuperset(order):
                    return OrderedDict(sorted(l, key=lambda x: order.get(x[0], 0)))
            return OrderedDict(sorted(l))
        if isinstance(stuff, list):
            return [process(x) for x in stuff]
        return stuff
    return process


"""
def sort_ordered_dictionary(dictionary):
    return {k: sort_ordered_dictionary(v) if isinstance(v, dict) else v
            for k, v in sorted(dictionary.items())}
"""


def sort_ordered_dictionary(od):
    res = OrderedDict()
    for k, v in sorted(od.items()):
        if isinstance(v, dict):
            res[k] = sort_ordered_dictionary(v)
        else:
            res[k] = v
    return res


def jsonprettyprint_template(template_data):
    """Summary.

    Args:
        template_data (TYPE): Description

    Returns:
        TYPE: Description
    """
    ordered_dict_data = OrderedDict(json.loads(json.dumps(template_data, sort_keys=True, cls=cfn_constructors.DateTimeEncoder)))
    sorted_template_data = sort_ordered_dictionary(ordered_dict_data)
    # log.debug("Checking unicode sorted_template_data: %s" % (type(sorted_template_data)))
    # import pprint
    # pprint.pprint(sorted_template_data)
    # pretty_json = template_data

    try:
        pretty_json = json.dumps(collections.OrderedDict(sorted(sorted_template_data.items(), key=lambda k_v: sort_order.index(k_v[0]))),
                                 indent=4,
                                 cls=cfn_constructors.DateTimeEncoder)
        log.info("JSON Pretty Print formatting template with CFN sort order")
    except Exception as e:
        log.warn(e)
        # import pprint
        # pprint.pprint(template_data)
        traceback.print_exc(file=sys.stdout)
        # traceback.print_exc(file=sys.stdout)
        # print(type(template_data))
        # print(type(sorted_template_data))
        # raise Exception("Unicode not Dict")
    return pretty_json


def load_data_structure(file_name):
    """Summary.

    Args:
        file_name (TYPE): Description

    Returns:
        TYPE: Description
    """
    extension = file_name.split('.')[-1].lower()
    if not os.path.isfile(file_name):
        log.warn("Config file not found: %s" % (file_name))
    else:
        try:
            log.debug("Loading config: %s" % (file_name))

            if extension == "yaml":
                log.debug("Config is yaml")
                data = ruamel.yaml.load(file_name)
                log.info("Loaded config from: %s" % (file_name))
                return data
            elif extension == "json":
                log.debug("Config is json")
                with open(file_name, 'r') as json_data:
                    data = json.loads(json_data.read())
                    json_data.close()
                log.info("Loaded config from: %s" % (file_name))
                return data
            else:
                log.warn("File format specified not supported: %s" % (file_name))
                return {}
        except Exception as e:
            log.warn("Failed loading config from: %s" % (file_name))
            log.warn(e)


def save_data_structure(file_name, data, sorted_keys=True, overwrite_existing=False, merge_new_keys=False):
    """Summary.

    Args:
        file_name (TYPE): Description
        data (TYPE): Description
        sorted_keys (bool, optional): Description
        overwrite_existing (bool, optional): Description
        merge_new_keys (bool, optional): Description

    Returns:
        TYPE: Description
    """
    extension = file_name.split('.')[-1].lower()
    try:
        if not os.path.isfile(file_name) or overwrite_existing:
            if overwrite_existing:
                log.info("Over writing existing file: %s" % (file_name))
            directory = os.path.dirname(file_name)
            if not os.path.exists(directory):
                os.makedirs(directory)

            if extension == "json":  # not(os.path.isfile(file_name)): # or args.overwrite_existing:
                with open(file_name, 'w') as output_file:
                    output_file.write(json.dumps(data, indent=4, sort_keys=sorted_keys))
                    output_file.close()
                    log.info('Written: %s' % (file_name))
                    return True

            elif extension == "yaml":
                with open(file_name, 'w') as output_file:
                    ruamel.yaml.dump(data, output_file, Dumper=ruamel.yaml.RoundTripDumper)
                    output_file.close()
                    log.info('Written: %s' % (file_name))
                    return True
            else:
                log.warn("File format specified not supported: %s" % (file_name))
                return False
        else:
            log.info("Existing file detected: %s" % (file_name))
            existing_data = load_data_structure(file_name)
            if merge_new_keys:
                for k, v in data:
                    if k not in existing_data:
                        log.info("Adding new config item [%s] to existing file %s" % (k, file_name))
                        existing_data[k] = data[k]
                        return save_data_structure(file_name=file_name, data=existing_data, sorted_keys=sorted_keys, overwrite_existing=True)

    except Exception as e:
        log.warn(e)
        traceback.print_exc()
        return False


def save_scrape_data(url, data):
    file_name = "docs/aws-scrapes/%s.json" % (inflection.parameterize(url))
    save_data_structure(file_name, data, sorted_keys=True, overwrite_existing=True, merge_new_keys=False)


def setup_logging(logger, verbosity=None):
    """Summary.

    Args:
        logger (TYPE): Description
        verbosity (None, optional): Description
    """
    import logging
    import sys
    from colorlog import ColoredFormatter
    # from pythonjsonlogger import jsonlogger

    global log
    log = logger

    if verbosity is None:
        verbosity = logging.INFO

    if len(log.handlers) == 0:
        logging.basicConfig(filename='debug.log', level=verbosity)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter_console_colour = "%(log_color)s%(levelname)-8s %(module)s:%(lineno)d- %(name)s%(reset)s %(blue)s%(message)s"

        """
        # create kinesis handler
        # formatter_json = jsonlogger.JsonFormatter()
        q = queue.Queue()
        kinesis_handler = kinesishandler.KinesisHandler(10, q)
        kinesis_handler.setFormatter(formatter_json)
        kinesis_handler.setLevel(logging.INFO)
        worker = kinesishandler.Worker(q, "aws-account-base-stream", region="us-east-1")
        worker.start()
        log.addHandler(kinesis_handler)
        """

        # add std out handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(verbosity)
        colored_formatter = ColoredFormatter(
            formatter_console_colour,
            datefmt='%H:%M:%S ',
            reset=True,
            log_colors={
                'DEBUG': 'white',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'orange',
                'CRITICAL': 'red',
            }
        )
        console_handler.setFormatter(colored_formatter)
        log.addHandler(console_handler)
        log.debug("logging initialized")


"""
def get_cfn_stack_policy(cfn_template):

    actions = ["Update:Modify","Update:Replace","Update:Delete"]
    tpl = {     "Statement": [
                {   "Effect": "Deny",
                    "Action": actions,
                    "Principal": "*",
                    "Resource": "*",
                    "Condition": {
                    "StringEquals": {"ResourceType": ["AWS::CloudFormation::Stack"]}}},{
                "Effect": "Allow",
                "Action": "Update:*",
                "Principal": "*",
                "Resource": "*"}
                ]
    }
    for resource in cfn_template["Resources"]:
        constraint = {
                "Effect": "Deny",
                "Action": actions,
                "Principal": "*",
                "Resource": resource
        }
        tpl["Statement"].append(constraint)
    return tpl
"""


def clean_whitespace(pString):
    pString = pString.replace("  ", " ")
    if "  " in pString:
        return clean_whitespace(pString)
    else:
        return pString.strip(" ")


def main():

    # log = LoggerManager().getLogger(__name__)
    # log.setLevel(level=logging.DEBUG)
    # log = logging.getLogger()
    setup_logging(log, verbosity=logging.DEBUG)

    # construct the argument parse and parse the arguments

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=False, default=expanduser('~/.cfconfig'), help="output directory prefix for troposphere dsl versions")
    args = vars(ap.parse_args())

    load_config(file_name=args["config"])


aws_product_region_endpoints = load_json(FILE_REFERENCE_PRODUCT_REGION_ENDPOINTS)
aws_product_compliance_info = load_json(FILE_REFERENCE_AWS_PRODUCT_COMPLIANCE)


if __name__ == "__main__":
    # main()
    import cf_decorator
    schema = cf_decorator.parse_cloudformation_resource_specification(cfrs_spec_file)

    example_file = "reference/aws-docs/cloudformation-templates-ap-southeast-2/0039952412_1416613611_Windows_Single_Server_Active_Directory.template.cfn.json"
    custom_sort = make_custom_sort([["Type", "Metadata", "Properties"]])
    custom_properties_sort = make_custom_sort([["Type", "Metadata", "Name", "Description", "Comment"]])
    cftemplate = load_json(example_file)
    print(list(cftemplate.keys()))
    for resource_name in cftemplate["Resources"]:
        try:
            print(cftemplate["Resources"][resource_name]["Type"])
            cftemplate["Resources"][resource_name] = custom_sort(cftemplate["Resources"][resource_name])
            # cftemplate["Resources"][resource_name] = OrderedDict(cftemplate["Resources"][resource_name])
            cftemplate["Resources"][resource_name]["Properties"] = custom_properties_sort(OrderedDict(cftemplate["Resources"][resource_name]["Properties"]))
        except Exception as e:
            print(e)
    try:
        cftemplate["Parameters"] = OrderedDict(cftemplate["Outputs"])
    except Exception as e:
        pass

    try:
        cftemplate["Outputs"] = OrderedDict(cftemplate["Outputs"])
    except Exception as e:
        pass

    print(json.dumps(list(schema.keys()), indent=4))
    # import pprint
    # cpprint.pprint(cftemplate)
