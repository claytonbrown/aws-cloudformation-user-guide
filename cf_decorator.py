#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Summary
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html
"""
import argparse
import logging
import pprint
import cf_util
import copy
import hashlib
import datetime
import os

timestamp = datetime.date.today().strftime("%Y-%m-%d")

log = logging.getLogger(__name__)
cf_util.setup_logging(log, logging.INFO)
json = cf_util.json

schema = None
template_messages = {}
cfn_schema = {}
# IAM_POLICIES = None
# CFN_BASE_SCHEMA = None
# cf_resources_by_region_data = None
# aws_product_descriptions_data = None

IAM_POLICIES = cf_util.json.loads(cf_util.basetemplate)
CFN_BASE_SCHEMA = cf_util.json.loads(cf_util.basetemplate)
resources_by_region_data = None
schema = {}
all_properties_docs = {}

rule_id = 0


best_practices = {}


defaults = {
    "Parameters": {
        "NotificationsARN": {
            "Type": "String",
            "Description": "Stack/Service Notifications ARN"
        },
        "LoggingDestination": {
            "Type": "String",
            "Description": "Loggin destination"
        },
        "LoggingDestinationRegion": {
            "Type": "String",
            "Description": "Loggin destination region"
        },
        "KmsKeyId": {
            "Type": "String",
            "Description": "KMS Key ID on source system of data"
        },
        "KmsKeyIdDestination": {
            "Type": "String",
            "Description": "KMS Key ID on target system of data"
        },
        "VpcId": {
            "Type": "String",
            "Description": "VPC ID"
        },
        "ImageId": {
            "Type": "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>"
        },
        "Tenancy": {
            "Type": "String",
            "AllowedValues": ["default", "dedicated", "host"],
            "Default": "default"
        },
        "PublicIngressCIDR": {
            "Type": "String",
            "Description": "Acceptable Ip Range for Public Ingress Traffic",
            "MinLength": "9",
            "MaxLength": "18",
            "Default": "0.0.0.0/0",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "ConstraintDescription": "must be a valid IP CIDR range of the form x.x.x.x/x."
        },
        "PublicEgressCIDR": {
            "Type": "String",
            "Description": "Acceptable Ip Range for Public Egress Traffic",
            "MinLength": "9",
            "MaxLength": "18",
            "Default": "0.0.0.0/0",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "ConstraintDescription": "must be a valid IP CIDR range of the form x.x.x.x/x."
        },
        "DBAccessSecurityGroups": {
            "Type": "List<AWS::EC2::SecurityGroup::Id>",
            "Description": "DB Access Security Group"
        }
    },
    "ResourceAttributes": {
        "AWS::EC2::Volume": {
            "DeletionPolicy": "Snapshot"
        },
        "AWS::ElastiCache::CacheCluster": {
            "DeletionPolicy": "Snapshot"
        },
        "AWS::ElastiCache::ReplicationGroup": {
            "DeletionPolicy": "Snapshot"
        },
        "AWS::RDS::DBInstance": {
            "DeletionPolicy": "Snapshot"
        },
        "AWS::RDS::DBCluster": {
            "DeletionPolicy": "Snapshot"
        },
        "AWS::Redshift::Cluster": {
            "DeletionPolicy": "Snapshot"
        }
    },
    "ResourceProperties": {
        "AWS:RESOURCE:EXAMPLE": {
            "Property": "value",
            "Encrypted": True,
            "KmsKeyId": {"Ref": "KmsKeyId"},
            "Tags": copy.deepcopy(cf_util.tagging_standards)
        },
        "AWS::S3::Bucket": {
            "VersioningConfiguration": {"Status": "Enabled"},
            "LoggingConfiguration": {
                "DestinationBucketName": {"Ref": "logging_bucket"},
                "LogFilePrefix": {"Fn::Join": ["/", ["s3", {"Ref": "AWS::Region"}, {"Ref": "AWS::StackName"}, "{{resource_name}}"]]}

            }
        },
        "AWS::CloudFront::StreamingDistribution": {
            "StreamingDistributionConfig": {
                "Logging": {
                    "Bucket": {"Ref": "LoggingDestination"},
                    "Enabled": True,
                    "Prefix": {"Fn::Join": ["/", ["cloudfront", {"Ref": "AWS::Region"}, {"Ref": "AWS::StackName"}, "{{resource_name}}"]]}
                }
            }
        },
        "AWS::ElasticLoadBalancing::LoadBalancer": {
            "CrossZone": True,
            "AccessLoggingPolicy": {
                "EmitInterval": 5,
                "Enabled": True,
                "S3BucketName": {"Ref": "LoggingDestination"},
                "S3BucketPrefix": {"Fn::Join": ["/", ["elb", {"Ref": "AWS::Region"}, {"Ref": "AWS::StackName"}, "{{resource_name}}"]]}
            }
        },
        "AWS::SSM::MaintenanceWindowTask": {
            "LoggingInfo": {
                "S3Bucket": {"Ref": "LoggingDestination"},
                "Region": {"Ref": "LoggingDestinationRegion"},
                "S3Prefix": {"Fn::Join": ["/", ["ssm", {"Ref": "AWS::Region"}, {"Ref": "AWS::StackName"}, "{{resource_name}}"]]}
            }
        }
    },
    "ResourceTemplates": {
        "AWS::Logs::LogGroup": {
            "Type": "AWS::Logs::LogGroup",
            "Properties": {
                "LogGroupName": "{{name}}",
                "RetentionInDays": 14
            }
        }
    }
}
# TODO
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rds-eventsubscription.html


def validate_signature(data):
    signed_signed, signature = sign_template(data)
    if data["Metadata"]['cfn_signature'] == signature:
        log.info("Template Signature validated: %s " % (signature))
        return True
    else:
        log.info("Template Signature failed signature validation: %s " % (signature))
        return False


def sign_template(data):
    # collate / sort only elements required to be signed
    content = {}

    if "Mappings" in data:
        content["Mappings"] = data["Mappings"]

    if "Parameters" in data:
        content["Parameters"] = data["Resources"]

    if "Resources" in data:
        content["Resources"] = data["Resources"]

    if "Conditions" in data:
        content["Conditions"] = data["Conditions"]

    if "Transform" in data:
        content["Transform"] = data["Transform"]

    content_string = json.dumps(content, sort_keys=True)
    # todo store secret safely per customer
    secret = b'nomoresecrets'
    m = hashlib.md5()
    m.update(secret + content_string.encode('utf-8'))
    signature = m.hexdigest()

    if "Metadata" not in data:
        data["Metadata"] = {}
    data["Metadata"]['cfn_signature'] = signature

    return data, signature


def decorate_policy(data, ):
    return data



def add_cfn_policy( control_class, policy_type, resource_type, resource_property, property_type, property_docs, expected_value, default_value, rule_description, wa_ref='wa-sec-1-1', wa_why='wa say do stuff becuase much good'):
    global rule_id
    global schema
    global cfn_schema
    global all_properties_docs

    ## GENERATE BEST PRACITCES HACK
    service = resource_type.split('::')[1]
    service_ref = "%s.%s" % (resource_type, resource_property )
    best_practice = {
        "PrimaryService": service,
        "Status": "Pending",
        #"Title": "Ensure %s - %s.%s = %s (%s)" % (control_class, policy_type, resource_type, resource_property, rule_description, expected_value ),
        "Title": "Ensure %s " % (policy_type),
        "Why": "%s : %s" % (wa_ref, wa_why),
        "How": rule_description, # TODO :scrap docs - cf_util.scrape_cfn_property_docs(property_docs),
        "CFN-Docs": property_docs,
        "ControlClass": control_class,
        "RelatedServices": [service],
        "Tags": [resource_type.split('::')[1], wa_ref, control_class, policy_type, resource_type, resource_property]
    }
    if service not in best_practices:
        best_practices[service] = {}
    best_practices[service][service_ref] = best_practice
    log.warning(json.dumps(best_practice, indent=4, sort_keys=True))



    # maintain list of all properties processed via docs
    log.debug(property_docs)
    keyname = "%s.%s" % (resource_type, resource_property)
    all_properties_docs[keyname] = {
                                            "policy_type": policy_type,
                                            "rule_description": rule_description,
                                            "default_value": default_value,
                                            "expected_value": expected_value,
                                            "resource_type": resource_type,
                                            "resource_property": resource_property,
                                            "property_type": property_type,
                                            "property_docs": property_docs,
                                            "keyname": keyname
    }
    log.debug(all_properties_docs[keyname])

    warning_type = "Violation::FAILING_VIOLATION"
    if policy_type in ["optional"]:
        warning_type = "Violation::WARNING"


    ## SUMMARIZE POLICIES
    if policy_type not in cfn_schema:
        cfn_schema[policy_type] = []
    cfn_schema[policy_type].append("%s.%s" % (resource_type, resource_property))

    ## ASIGN DEFAULTS
    if resource_type not in defaults["ResourceProperties"]:
        defaults["ResourceProperties"][resource_type] = {}
    defaults["ResourceProperties"][resource_type]["Tags"] = default_value

    ## ADD RESOURCE TO SCHEMA
    if resource_type not in schema:
        schema[resource_type] = {}

    ## MAINTAIN EXPECTATIONS IN SCHEMA
    if policy_type not in schema[resource_type]:
        schema[resource_type] = {}
        schema[resource_type][policy_type] = {}

    ## ENFORCE EXPECTATIONS
    if "expected" not in cfn_schema[resource_type]:
        cfn_schema[resource_type]["expected"] = {}

    cfn_schema[resource_type]["expected"][resource_property] = default_value

    if "expected" not in schema[resource_type]:
        schema[resource_type]["expected"] = {}

    #if resource_property not in schema[resource_type]["expected"]:
    schema[resource_type]["expected"][resource_property] = {}
    schema[resource_type]["expected"][resource_property]["value"] = expected_value
    schema[resource_type]["expected"][resource_property]["type"] = property_type
    schema[resource_type]["expected"][resource_property]["docs"] = property_docs
    log.info("Adding expected policy: %s->%s = %s" % (resource_type, resource_property, expected_value))

    rule_id += 1
    # REF - https://github.com/stelligent/cfn_nag/blob/master/migration.md
    if expected_value == "type:exists":
        if default_value is not None:
            rule_description = "%s property [%s] should exist, consider default values of [ %s ] " % (resource_type, resource_property, default_value)
        else:
            rule_description = "%s property [%s] should exist" % (resource_type, resource_property)
        cfn_nag_template = """
require 'cfn-nag/violation'
require_relative 'base'

class {class_name} < BaseRule
  def rule_text
    "[{policy_type}] {rule_description}"
  end

  def rule_type
    {warning_type}
  end

  def rule_id
    'C-{rule_id}'
  end

  def audit_impl(cfn_model)
    violating_resources = cfn_model.resources_by_type('{resource_type}').select do |resource|
      resource.{resource_property}.nil?
    end

    violating_resources.map {{ |violating_resource| violating_resource.logical_resource_id }}
  end
end
        """
    else:
        cfn_nag_template = """
require 'cfn-nag/violation'
require_relative 'base'

class {class_name} < BaseRule
  def rule_text
    "[{policy_type}] {rule_description}"
  end

  def rule_type
    {warning_type}
  end

  def rule_id
    'C-{rule_id}'
  end

  def audit_impl(cfn_model)
    violating_resources = cfn_model.resources_by_type('{resource_type}').select do |resource|
      resource.{resource_property}.nil? || resource.{resource_property}.to_s.downcase != '{expected_value}'
    end

    violating_resources.map {{ |violating_resource| violating_resource.logical_resource_id }}
  end
end
        """
    nag_class_name = "Custom%s%sRule" % (resource_type.replace(":", ""), resource_property)
    # /usr/local/share/ruby/gems/2.3/gems/cfn-nag-0.3.20/lib/cfn-nag/custom_rules/
    nag_file_name = "cfn_nag/spec/custom_rules/%s.rb" % (nag_class_name)
    rule = cfn_nag_template.format(class_name=nag_class_name,
                                   rule_id= "%04d" % rule_id,
                                   resource_type=resource_type,
                                   resource_property=resource_property.lower(),
                                   rule_description=rule_description,
                                   expected_value=expected_value.lower(),
                                   policy_type=policy_type,
                                   warning_type=warning_type
                                   )
    with open(nag_file_name, 'w') as custom_rule:
        log.debug(rule)
        custom_rule.write(rule)
        log.info("Written Custom Nag Rule: %s" % (nag_file_name))




def parse_cloudformation_resource_specification(file_location=cf_util.cfrs_spec_file, cache_file='/tmp/cfn-schema-%s.json' % (timestamp)):
    global cfn_schema
    if False and cache_file is None or not os.path.isfile(cache_file):
        log.info("Parsing: %s" % (file_location))
        CFRSmodel = None
        with open(file_location) as data_file:
            CFRSmodel = json.load(data_file)

        # For ALL CFN ResourceTypes
        for resource in CFRSmodel["ResourceTypes"]:

            cfn_schema[resource] = {
                "properties": [],
                "required": [],
                "optional": [],
                "expected": {},
                "all": []
            }
            defaults["ResourceProperties"][resource] = {}

            # For ALL CFN Resource Properties / Enforce Standards
            for property_name in CFRSmodel["ResourceTypes"][resource]["Properties"]:


                property_docs = CFRSmodel["ResourceTypes"][resource]["Properties"][property_name]["Documentation"]
                try:
                    property_type = CFRSmodel["ResourceTypes"][resource]["Properties"][property_name]["PrimitiveType"]
                except:
                    property_type = CFRSmodel["ResourceTypes"][resource]["Properties"][property_name]["Type"]
                finally:
                    assert(property_type is not None)

                log.debug("Inspecting property name: %s (%s): %s" % (property_name, property_type, property_docs) )

                cfn_schema[resource]["all"].append(property_name)
                if CFRSmodel["ResourceTypes"][resource]["Properties"][property_name]["Required"] is True:
                    cfn_schema[resource]["required"].append(property_name)

                # TAGGING
                if property_name == 'Tags':

                    add_cfn_policy( control_class='detective',
                                    policy_type='taggable',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value= copy.deepcopy(cf_util.tagging_standards),
                                    rule_description='Enforce Tag usage for %s using the %s property' % (resource, property_name)
                                    )

                # NETWORK / ISOLATION RULES
                elif property_name in ['VpcId', 'EC2VpcId']:

                    add_cfn_policy( control_class='preventative',
                                    policy_type='vpc-protection',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value= {
                                        "Ref": "VpcId"
                                    },
                                    rule_description='Enforce VPC usage for %s using the %s property' % (resource, property_name)
                                    )

                elif property_name == 'AvailabilityZone':

                    add_cfn_policy( control_class='preventative',
                                    policy_type='zone-specific',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value=None,
                                    rule_description='Enforce MultiAZ/VPC usage for %s using the %s property' % (resource, property_name)
                                    )

                elif property_name == 'Tenancy':

                    add_cfn_policy( control_class='preventative',
                                    policy_type='tenancy',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value={
                                        "Ref": "Tenancy" # enforce tenancy model
                                    },
                                    rule_description='%s has a property [%s] which should elected/specified' % (resource, property_name)
                                    )


                ## ENCRYPTION CONTROLS
                elif property_name.lower() in ["encryptionkey", "kmsmasterkeyid", "kmskeyid", "volumeencryptionkey"]:

                    add_cfn_policy( control_class='preventative',
                                    policy_type='kms-encryption-key',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value={
                                        "Ref": "KmsKeyId" # enforce use of KMS key
                                    },
                                    rule_description='%s property [%s] should exist and be {"Ref": "KmsKeyId"}' % (resource, property_name)
                                    )

                elif property_name in [ "Encrypted", "EnableSsl", "StorageEncrypted", "CacheDataEncrypted", "TransitEncryptionEnabled",
                                        "UserVolumeEncryptionEnabled", "RootVolumeEncryptionEnabled", "EnableLogFileValidation",
                                        "AtRestEncryptionEnabled", "EnableKeyRotation"]:

                    add_cfn_policy( control_class='preventative',
                                    policy_type='encrypted',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value=True,
                                    rule_description="%s property [%s] should exist and be True" % (resource, property_name)
                                    )
                    #  TODO: If you enable TransitEncryptionEnabled, then you must also specify CacheSubnetGroupName.

                elif property_name == "BucketEncryption":

                    add_cfn_policy( control_class='preventative',
                                    policy_type='encrypted',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value={
                                        "ServerSideEncryptionConfiguration": {
                                            "KMSMasterKeyID": {
                                                "Ref": "KmsKeyId"
                                            },
                                            "SSEAlgorithm": "aws:kms"
                                        }
                                    },
                                    rule_description='%s property [%s] should exist and be {"Ref": "KmsKeyId"}' % (resource, property_name)
                                    )

                elif property_name == "EncryptionType":

                    add_cfn_policy( policy_type='encrypted',
                                    control_class='preventative',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:string:KMS",
                                    default_value="KMS",
                                    rule_description="%s property [%s] should exist and be set to 'KMS'" % (resource, property_name)
                                    )

                elif property_name == "StreamEncryption":

                    add_cfn_policy( policy_type='encrypted',
                                    control_class='preventative',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:string:KMS",
                                    default_value= {
                                        "EncryptionType": "KMS",
                                        "KeyId": {
                                            "Ref": "KmsKeyId"
                                        }
                                    },
                                    rule_description="%s property [%s] should exist and be set to 'KMS' with reference to KmsKeyID parameter" % (resource, property_name)
                                    )

                # IAM ROLES

                # LOGGING STANDARDS
                elif property_name in ["IsLogging", "EnableLogFileValidation"]:

                    add_cfn_policy( policy_type='logging',
                                    control_class='detective',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value=True,
                                    rule_description="%s property [%s] should exist and be set to 'True'" % (resource, property_name)
                                    )

                elif "StreamingDistributionConfig" in resource and property_name in ["Logging"]:

                    #config =  # "<servicename>/<region>/<resource>"
                    #config =  # "cloudfront/{{aws_region}}/{{resource_name}}"
                    add_cfn_policy( control_class='detective',
                                    policy_type='logging',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value= {
                                        "Logging": {
                                            "Bucket": {
                                                "Ref": "LoggingDestination"
                                            },
                                            "Enabled": True,
                                            "Prefix": {
                                                "Fn::Join" : [ "/", [
                                                    "cloudfront",
                                                    {"Ref": "AWS:Region"}
                                                    ]
                                                ]
                                            }
                                        }
                                    },
                                    rule_description="%s property [%s] should exist and be set to 'True'" % (resource, property_name)
                                    )

                elif property_name in [ "AccessLoggingPolicy",
                                        "CloudWatchLoggingOptions",
                                        "CloudWatchLogsLogGroupArn",
                                        "CloudWatchLogsRoleArn",
                                        "DeliverLogsPermissionArn",
                                        "FieldLogLevel",
                                        "LogConfig",
                                        "LogConfiguration",
                                        "LogDriver",
                                        "LogFilePrefix",
                                        "Logging",
                                        "LoggingConfiguration",
                                        "LoggingInfo",
                                        "LoggingLevel",
                                        "LoggingProperties",
                                        "LogGroupName",
                                        "LogPaths",
                                        "LogStreamName",
                                        "LogUri",
                                        "QueryLoggingConfig" ]:

                    add_cfn_policy( control_class='detective',
                                    policy_type='logging',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value=None,
                                    rule_description="%s property [%s] should be configured" % (resource, property_name)
                                    )

                # HIGH AVAIALBILITY
                elif property_name in ["EnableDnsHostnames", "EnableDnsSupport", "EnableAutoHealing", "AutomaticFailoverEnabled", ""]:

                    add_cfn_policy( control_class='detective',
                                    policy_type='highavailability',
                                    resource_type=resource,
                                    resource_property=property_name,
                                    property_type=property_type,
                                    property_docs=property_docs,
                                    expected_value="type:exists",
                                    default_value=True,
                                    rule_description="%s property [%s] should exist and be set to 'True'" % (resource, property_name)
                                    )

                else:
                    if "logging" in property_name.lower() or "enable" in property_name.lower() or "policy" in property_name.lower():
                        log.warning("No Policy For Resource: %s Property: %s" % (resource, property_name))
                    cfn_schema[resource]["optional"].append(property_name)


            # SET ENFORCABLE PROPERTIES
            cfn_schema[resource]["enforced"] = list(
                                                    set(list(cfn_schema[resource]["expected"].keys()) + cfn_schema[resource]["required"])
                                                )

            log.info("\n\n%s: %s\n" % (resource, json.dumps(cfn_schema[resource], indent=5, sort_keys=True)))

        cf_util.save_data_structure(cf_util.FILE_CFRS_SUMMARY, cfn_schema, sorted_keys=True, overwrite_existing=True)

        expectations = {}
        for k, v in all_properties_docs.items():
            resource, property = k.split('.')
            if resource not in expectations:
                expectations[resource] = {}
            expectations[resource][property] = v
        cf_util.save_data_structure("reference/cfrs_searches/all_expectations.json", expectations, sorted_keys=True, overwrite_existing=True)


        cf_util.save_data_structure(cache_file, cfn_schema, sorted_keys=True, overwrite_existing=True)
        cf_util.save_data_structure(cf_util.FILE_CFRS_DEFAULTS, defaults, sorted_keys=True, overwrite_existing=True)
        cf_util.save_data_structure(cf_util.FILE_BEST_PRACTICES, best_practices, sorted_keys=True, overwrite_existing=True)

        log.warning("Saved CFN schema to cache file: %s" % (cache_file))
    else:
        log.warning("Loading CFN schema from cache file: %s" % (cache_file))
        cfn_schema = cf_util.load_data_structure(cache_file)


    return cfn_schema


def add_template_message(criticality, message):
    criticality = criticality.lower()
    error_types = ["debug", "info", "warn", "error", "critical"]

    options = {
        "debug": log.debug,
        "info": log.info,
        "warn": log.warn,
        "error": log.critical,
        "critical": log.critical
    }
    # shebang logging message at appropriate level
    # options[criticality](message)
    log.debug(message)

    if criticality not in error_types:
        criticality = error_types[0]

    if criticality not in template_messages.keys():
        template_messages[criticality] = list()

    template_messages[criticality].append(message)


def decorate_template(data, pSchema=None, pRegionData=None, pComplianceData=None):
    global template_messages
    template_messages = {}

    # cfn_schema = (pSchema, parse_cloudformation_resource_specification(file_location=cf_util.cfrs_spec_file))[pSchema == None]
    cf_resources_by_region_data = (pRegionData, cf_util.load_json(cf_util.cf_resources_by_region_file))[pRegionData is None]
    aws_product_descriptions_data = (pComplianceData, cf_util.load_json(cf_util.FILE_REFERENCE_AWS_PRODUCT_COMPLIANCE))[pComplianceData is None]

    now = "{:%Y-%m-%d : %I:%M:%S}".format(datetime.datetime.now())

    # create high level default attributes
    for template_property in cf_util.sort_order:
        if template_property not in data.keys():
            data[template_property] = {}
            # add_template_message("Added default property: %s" % (template_property), criticality='info', errors=errors)

    data["Metadata"]["cfn_decorator"] = now
    # add_template_message('debug', "Marked template with date time it was processed: %s" % (now), errors)

    # CHECK BASIC RESOURCE TYPES
    template_resource_types = []
    for resource_name in data["Resources"].keys():
        resource_type = data["Resources"][resource_name]["Type"]
        if "Custom::" not in resource_type:
            template_resource_types.append(resource_type)
        else:
            add_template_message('warn', "Custom Resource detected: %s [%s]" % (resource_type, resource_name))
            # log.warn("Custom Resource Type: %s" % (resource_type))

    unknown_resource_types = list(set(template_resource_types) - set(cf_resources_by_region_data["all_resource_types"]))
    if len(unknown_resource_types) > 0:
        # log.warn("Unknown resource types in template: %s" % (json.dumps(unknown_resource_types)))
        log.warn(json.dumps(template_resource_types))
        log.warn(json.dumps(cf_resources_by_region_data["all_resource_types"]))
        add_template_message("warn", "Unknown resource types in template: %s" % (json.dumps(unknown_resource_types)))

    # ASSESS TEMPLATE AGAINST REGIONAL SUPPORT
    supported_regions = []
    for region in cf_resources_by_region_data["regions"].keys():
        log.debug(json.dumps(cf_resources_by_region_data["regions"][region]))
        log.debug(region)
        if "resource_types" in cf_resources_by_region_data["regions"][region] and cf_resources_by_region_data["regions"][region]["resource_types"] is not None:
            if len(list(set(template_resource_types) - set(cf_resources_by_region_data["regions"][region]["resource_types"]))) == 0:
                log.debug("Template expected to work in region: %s" % (region))
                supported_regions.append(region)
    add_template_message("debug", "Adding Regions Supported to Template Metadata: %s" % (json.dumps(supported_regions)))
    data["Metadata"]["supported_regions"] = supported_regions

    # for all standard tags declared in config defaults
    for item in cf_util.tagging_standards:
        data["Parameters"][item["Value"]["Ref"]] = {"Type": "String", "Description": "Tagging standards for " + item["Key"]}
        add_template_message("info", "Added default tag: %s" % (item["Key"]))

    # ASSESS TEMPLATE AGAINST COMPLIANCE ATTESTATIONS
    compliance_scopes = []
    for scope in aws_product_descriptions_data["aws-cf-resource-compliance"].keys():
        # compare all resource types in template, with each scopes resources covered by attestation
        if len(list(set(template_resource_types) - set(aws_product_descriptions_data["aws-cf-resource-compliance"][scope]))) == 0:
            # if all resources used are covered by scope add to template attestations
            add_template_message("debug", "Template resources have compliance attestations for: %s" % (scope))
            compliance_scopes.append(scope)
    if len(compliance_scopes) == 0:
        compliance_scopes.append("none")

    # annotate template with compliance scopes
    data["Metadata"]["aws_compliance"] = compliance_scopes
    log.debug("Updating Template Metadata with Highest Compliance Attestation For ALL Resources: %s" % (json.dumps(compliance_scopes)))

    # additionally decorate attestation meta data for each resource within template
    for resource_name in data["Resources"].keys():

        # Assess compliance of resource type
        resource_type = data["Resources"][resource_name]["Type"]
        scope = "unknown"
        log.debug("resource_type: %s" % (resource_type))
        log.debug("aws_product_descriptions_data: %s" % (aws_product_descriptions_data.keys()))
        if "Custom::" not in resource_type and resource_type in aws_product_descriptions_data["aws-cf-resource-compliance"]:
            scope = aws_product_descriptions_data["aws-cf-resource-compliance"][resource_type]

        if "Tags" in data["Resources"][resource_name]:
            data["Resources"][resource_name]["Tags"].append({"Key": "aws_compliance", "Value": {scope}})
            log.warn("Tagging compliance scope [%s] to %s [%s] Tags[aws_compliance]" % (scope, resource_type, resource_name))

        if "Metadata" not in data["Resources"][resource_name]:
            data["Resources"][resource_name]["Metadata"] = {}

        data["Resources"][resource_name]["Metadata"]["aws_compliance"] = scope
        # add_template_message("info", "Annotating resource_type compliance scope [%s] to %s [%s] Metadata" % (scope, resource_type, resource_name))
        add_template_message("debug", "Annotating compliance scope [%s] to [%s] Metadata" % (scope, resource_name))

    data["Parameters"]["TagsCompliance"] = {
        "Type": "String",
        "Description": "Tagging standards for compliance alignment",
        "AllowedValues": compliance_scopes,
        "Default": compliance_scopes[0]
    }
    add_template_message("info", "Adding TagCompliance parameter constrained to valid scopes: %s" % (",".join(compliance_scopes)))

    for property in CFN_BASE_SCHEMA.keys():
        if property not in data:
            data[property] = CFN_BASE_SCHEMA[property]

    # For every resources in current template
    for resource_name in data["Resources"]:
        resource = data["Resources"][resource_name]
        log.debug("%40s : %s" % (resource_name, resource["Type"]))

        # Apply resource property defaults if they exist
        if "Properties" in resource:
            if resource["Type"] in defaults["ResourceProperties"]:

                # Determine if any default properties have been declared in config or this ResourceType
                resource_type_defaults = defaults["ResourceProperties"][resource["Type"]]

                # For every default property name declared
                for default_property in resource_type_defaults:

                    # Assign any resource type default properties specified in config to this instance of resource type
                    resource["Properties"][default_property] = resource_type_defaults[default_property]
                    add_template_message("info", "Injecting %s property defaults for '%s' on %s" % (resource["Type"], default_property, resource_name))

                    # If resource is a Map/Dictionary of KeyValue pars which has a key called  "Ref"

                    if isinstance(resource["Properties"][default_property], dict) and "Ref" in resource["Properties"][default_property]:
                        log.debug("Resource property contains a reference: %s" % (resource["Properties"][default_property]["Ref"]))

                        # Get the default value referenced in the resources
                        reference_name = resource_type_defaults[default_property]["Ref"]

                        # If value referenced is in default parameters, but not in current template parameters
                        if reference_name in defaults["Parameters"] and reference_name not in data["Parameters"]:
                            log.debug("%s found in default" % (reference_name))

                            # Add template parameter to template based on config paramtetersdefaults
                            data["Parameters"][reference_name] = defaults["Parameters"][reference_name]
                            add_template_message("info", "Adding necessary template parameter: %s" % (reference_name))

                if resource["Type"] == "AWS::AutoScaling::AutoScalingGroup":
                    add_template_message("info", "Enforcing PropagateAtLaunch for tags on AutoScalingGroup: %s" % (resource_name))

                    # Ensure Tags existi
                    if "Tags" not in data["Resources"][resource_name]["Properties"]:
                        data["Resources"][resource_name]["Properties"]["Tags"] = copy.deepcopy(cf_util.tagging_standards)

                    for tag in data["Resources"][resource_name]["Properties"]["Tags"]:
                        tag["PropagateAtLaunch"] = True

                # SECURITY GROUP RULES
                if resource["Type"] == "AWS::RDS::DBSecurityGroup":
                    log.debug("Examining AWS::RDS::DBSecurityGroup - %s" % (resource_name))
                    if "DBSecurityGroupIngress" in resource["Properties"]:
                        if type(resource["Properties"]["DBSecurityGroupIngress"]) == dict:
                            data["Resources"][resource_name]["Properties"]["DBSecurityGroupIngress"] = [data["Resources"][resource_name]["Properties"]["DBSecurityGroupIngress"]]
                            log.debug("Massaged to list property to list of properties")
                            add_template_message("info", "Coercing AWS::RDS::DBSecurityGroup dict property DBSecurityGroupIngress to list of dicts for - %s" % (resource_name))
                        else:
                            log.critical("DBSecurityGroupIngress type: %s " % (type(resource["Properties"]["DBSecurityGroupIngress"])))

                if resource["Type"] == "AWS::EC2::SecurityGroup":
                    log.debug("Examining AWS::EC2::SecurityGroup - %s" % (resource_name))

                    # Enforce VPC Ids on Security Groups
                    log.debug("Enforcing VpcIds")
                    if 'VpcId' not in resource["Properties"]:
                        add_template_message("info", "Injecting VpcId input parameter")
                        data["Resources"][resource_name]["Properties"]["VpcId"] = {"Ref": "VpcId"}
                        data["Parameters"]["VpcId"] = {"Type": "AWS::EC2::VPC::Id", "Description": "VPC ID for workload"}

                    # Enforce CF parameter value/ref for any 0.0.0.0/0 based rules on ingress rules
                    if 'SecurityGroupIngress' in resource["Properties"]:
                        for rule in resource["Properties"]["SecurityGroupIngress"]:
                            if 'CidrIp' in rule and rule["CidrIp"] == "0.0.0.0/0":
                                log.debug("Enforcing public SecurityGroupIngress through explicit PublicIngressCIDR passed as Params with default 0.0.0.0/0")
                                rule["CidrIp"] = {"Ref": "PublicIngressCIDR"}

                                if "PublicIngressCIDR" not in data["Parameters"]:
                                    data["Parameters"]["PublicIngressCIDR"] = defaults["Parameters"]["PublicIngressCIDR"]
                                    log.info("Adding PublicIngressCIDR parameter from defaults")

                    if 'DBSecurityGroupIngress' in resource["Properties"]:
                        for rule in resource["Properties"]["DBSecurityGroupIngress"]:
                            if 'CidrIp' in rule and rule["CidrIp"] == "0.0.0.0/0":
                                log.debug("Enforcing public DBSecurityGroupIngress through explicit PublicIngressCIDR passed as Params with default 0.0.0.0/0")
                                rule["CidrIp"] = {"Ref": "PublicIngressCIDR"}

                                if "PublicIngressCIDR" not in data["Parameters"]:
                                    data["Parameters"]["PublicIngressCIDR"] = defaults["Parameters"]["PublicIngressCIDR"]
                                    log.info("Adding PublicIngressCIDR parameter from defaults")

                    # Enforce Egress Rules through a Gateway
                    if 'SecurityGroupEgress' not in resource["Properties"]:
                        log.debug("Enforcing SecurityGroupEgress through a Gateway")
                        resource["Properties"]["SecurityGroupEgress"] = [{"IpProtocol": "tcp", "FromPort": "80", "ToPort": "80", "CidrIp": {"Ref": "OutboundGatewaySecurityGroupId"}}]
                        data["Parameters"]["OutboundGatewaySecurityGroupId"] = {"Type": "AWS::EC2::SecurityGroup::Id", "Description": "SecurityGroupID for Egress Gateway"}
                    else:
                        for rule in resource["Properties"]["SecurityGroupEgress"]:
                            if 'CidrIp' in rule and rule["CidrIp"] == "0.0.0.0/0":
                                log.debug("Enforcing public SecurityGroupEgress through explicit PublicEgressCIDR passed as Params with default 0.0.0.0/0")
                                rule["CidrIp"] = {"Ref": "PublicEgressCIDR"}

                                if "PublicEgressCIDR" not in data["Parameters"]:
                                    data["Parameters"]["PublicEgressCIDR"] = defaults["Parameters"]["PublicEgressCIDR"]
                                    log.info("Adding PublicEgressCIDR parameter from defaults")

                # Enforce Access Logging  on ELB
                if resource["Type"] == "AWS::ElasticLoadBalancing::LoadBalancer":
                    log.debug("Examining AWS::ElasticLoadBalancing::LoadBalancer - %s" % (resource_name))
                    if 'AccessLoggingPolicy' not in resource["Properties"]:
                        log.info("Injecting AccessLoggingPolicy into ELB - %s" % (resource_name))
                        data["Resources"][resource_name]["Properties"]["AccessLoggingPolicy"] = {"EmitInterval": 5, "Enabled": True, "S3BucketName": {"Ref": "ELBLoggingBucket"},
                                                                                                 "S3BucketPrefix": "ELB-AccessLogs/" + resource_name}
                        data["Parameters"]["ELBLoggingBucket"] = {"Type": "String", "Description": "S3 Bucket for ELB logs"}

        elif resource["Type"] == "AWS::CloudFormation::WaitConditionHandle":
            pass
        else:
            log.warn("Resource has no properties? [%s]" % (resource["Type"]))
            log.warn(json.dumps(resource))

    data, signature = sign_template(data)
    # log.debug(json.dumps(data, indent=4))
    # log.debug("Checking unicode issue: %s" % (type(data)))
    data["Metadata"]["cfn_decorator_messages"] = template_messages
    log.info(json.dumps(template_messages, indent=4, sort_keys=True))
    return data, template_messages


def main():
    schema = parse_cloudformation_resource_specification(file_location=cf_util.cfrs_spec_file)

    log.info("Parsed CloudFormation Resource Specification file: %s" % (cf_util.cfrs_spec_file))
    cf_util.save_data_structure(cf_util.FILE_REFERENCE_CFN_DECORATE_RULES, schema, sorted_keys=True)

    cf_util.setup_logging(log, verbosity=logging.DEBUG)

    # schema = parse_cloudformation_resource_specification()

    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="filename to read (else is STDIN)")
    ap.add_argument("--config", required=False, help="relatvive file location to generate or load defaults from ")
    ap.add_argument("--troposphere", required=False, help="generate troposphere template")
    ap.add_argument("--cfndsl", required=False, help="generate cfndsl template")
    ap.add_argument("--stackprotection", required=False, help="generate stackprotection policy")
    ap.add_argument("--defang", required=False, help="defang template")
    ap.add_argument("--layercake", required=False, help="layercake template")
    ap.add_argument("--compliance", required=False, default=False, help="annotate template/resources with compliance attestations")
    ap.add_argument("--overwrite-existing", required=False, default=False, action="store_true", help="Flag to over write existing template.json or template.yaml files")
    args = vars(ap.parse_args())

    pprint.pprint(args)

    if args["config"]:
        cf_util.save_data_structure("config/cf_defaults.yaml", defaults, sorted_keys=True, overwrite_existing=True)
    if args['overwrite_existing']:
        log.warn("overwrite existing file elected")
    data = ""
    if args['file'] is None:
        # read from filename passed
        log.debug("reading from std.in")
        # TODO: implement  STD.IN filter mode
    else:
        # read from STDIN
        log.debug("reading from file: %s " % (args['file']))
        data = json.load(open(args["file"], 'r'))

    data = decorate_template(data, schema, resources_by_region_data, aws_product_descriptions_data)

    # pprint.pprint(data)


if __name__ == "__main__":
    main()
