# ruamel.yaml > 0.15.8
# from functools import partial
# import pprint
import ruamel.yaml
import sys
from datetime import datetime, date
import json
import logging
import pprint
import pickle
import subprocess

log = logging.getLogger(__name__)
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-ref.html


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, date):
            return o.isoformat().split(':')[0]

        return json.JSONEncoder.default(self, o)


class AwsFnBase(ruamel.yaml.YAMLObject, dict):
    yaml_constructor = ruamel.yaml.constructor.RoundTripConstructor
    yaml_representer = ruamel.yaml.representer.RoundTripRepresenter

    def __init__(self, data, style):
        self._data = data
        self.style = style
        log.debug("initialized [%s]: %s" % (type(self), self.data))

    @property
    def data(self):
        # override this for custom behavior
        return self._data

    @classmethod
    def from_yaml(cls, loader, node, data_type=None):
        data_type = cls.data_type

        # log.debug("\n\ndata_type: [%s]" % (data_type))
        # pprint.pprint(node)

        if data_type == 'scalar':
            yield cls(loader.construct_scalar(node), style=node.style)

        elif data_type == 'seq':
            data = ruamel.yaml.comments.CommentedSeq()
            data._yaml_set_line_col(node.start_mark.line, node.start_mark.column)

            if node.flow_style:
                if node.flow_style is True:
                    data.fa.set_flow_style()
                elif node.flow_style is False:
                    data.fa.set_block_style()

            if node.comment:
                data._yaml_add_comment(node.comment)
            yield cls(data, style=node.flow_style)
            data.extend(loader.construct_rt_sequence(node, data, deep=True))

    @classmethod
    def to_yaml(cls, dumper, data, data_type=None):
        data_type = data_type or cls.data_type
        if data_type == 'scalar':
            return dumper.represent_scalar(cls.yaml_tag, data.data, style=data.style or None)
        elif data_type == 'seq':
            return dumper.represent_sequence(cls.yaml_tag, data.data, flow_style=data.style or None)

    @classmethod
    def get_data(self):
        return self._data

    @classmethod
    def __repr__(self):
        # object_dict = lambda o: {key.lstrip('_'): value for key, value in o.__dict__.items()}
        # return json.dumps(self, default=object_dict, allow_nan=False, sort_keys=False, indent=4)
        # pprint.pprint(dir(self.data))
        # log.debug("\n\n\n----\n%s" % (self.__dict__.items()))
        # pprint.pprint(vars(self))
        # data = self.value
        # return json.dumps(self, default=lambda x: x.__dict__)
        # def toJSON(self):
        try:
            # return str(pickle.dumps(self.__dict__))
            return json.dumps(self.dump())
        except Exception as e:

            log.warning(e, exc_info=True)
            return "{}"

        # return self.data

    #@classmethod
    # def __dict__(cls):
    #    return [type(cls), cls.data_type, json.dumps(cls.__dict__)]

    @classmethod
    def to_json(cls):
        return json.dumps(cls.__dict__, cls=DateTimeEncoder)


class Base64(AwsFnBase):
    yaml_tag = u'!Base64'
    data_type = 'scalar'

    @property
    def value(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Fn::Base64": self._data}, cls=DateTimeEncoder)


class FindInMap(AwsFnBase):
    yaml_tag = u'!FindInMap'
    data_type = 'seq'

    @property
    def map_name(self):
        return self._data[0]

    @property
    def top_level_key(self):
        return self._data[1]

    @property
    def second_level_key(self):
        return self._data[2]

    def __repr__(self):
        return json.dumps({"Fn::FindInMap": self._data}, cls=DateTimeEncoder)


class GetAtt(AwsFnBase):
    yaml_tag = u'!GetAtt'
    data_type = 'scalar'

    @property
    def logical_id(self):
        return self._data.split('.')[0]

    @property
    def attribute(self):
        return self._data.split('.')[1]

    def __repr__(self):
        return json.dumps({"Fn::GetAtt": self._data}, cls=DateTimeEncoder)


class GetAZs(AwsFnBase):
    yaml_tag = u'!GetAZs'
    data_type = 'scalar'

    @property
    def region(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Fn::ImportValue": self._data}, cls=DateTimeEncoder)


class ImportValue(AwsFnBase):
    yaml_tag = u'!ImportValue'
    data_type = 'scalar'

    @property
    def data(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Fn::GetAZs": self._data}, cls=DateTimeEncoder)


class Join(AwsFnBase):
    yaml_tag = u'!Join'
    data_type = 'seq'

    @property
    def delimiter(self):
        return self._data[0]

    @property
    def values(self):
        return self._data[1]

    def __repr__(self):
        return json.dumps({"Fn::Join": self._data}, cls=DateTimeEncoder)


class Select(AwsFnBase):
    yaml_tag = u'!Select'
    data_type = 'seq'

    @property
    def index(self):
        return self._data[0]

    @property
    def values(self):
        return self._data[1]

    def __repr__(self):
        return json.dumps({"Fn::Select": self._data}, cls=DateTimeEncoder)


class Split(AwsFnBase):
    yaml_tag = u'!Split'
    data_type = 'seq'

    @property
    def delimiter(self):
        return self._data[0]

    @property
    def source(self):
        return self._data[1]

    def __repr__(self):
        return json.dumps({"Fn::Split": self._data}, cls=DateTimeEncoder)


class Sub(AwsFnBase):
    yaml_tag = u'!Sub'
    data_type = 'seq'

    @property
    def source(self):
        return self._data[0]

    @property
    def values(self):
        if len(self._data) > 1:
            return self._data[1]
        return None

    @classmethod
    def from_yaml(cls, loader, node):
        try:
            data = super(Sub, cls).from_yaml(loader, node, data_type='seq')
        except yaml.constructor.ConstructorError:
            data = super(Sub, cls).from_yaml(loader, node, data_type='scalar')
        return data

    @classmethod
    def to_yaml(cls, dumper, data):
        if data.values is None:
            return super(Sub, cls).to_yaml(dumper, data, data_type='scalar')
        else:
            return super(Sub, cls).to_yaml(dumper, data, data_type='seq')

    def __repr__(self):
        return json.dumps({"Sub": self.data}, cls=DateTimeEncoder)


class Ref(AwsFnBase):
    yaml_tag = u'!Ref'
    data_type = 'scalar'

    """
        Example - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-ref.html
        JSON:
        { "Ref" : "logicalName" }

        YAML:
        Ref: logicalName
        !Ref logicalName
        """

    @property
    def logical_id(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Ref": self.data}, cls=DateTimeEncoder)


class Condition(AwsFnBase):
    yaml_tag = u'!Condition'
    data_type = 'scalar'

    @property
    def condition(self):
        return self._data

    def __dict__(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Condition": self.data}, cls=DateTimeEncoder)


class And(AwsFnBase):
    yaml_tag = u'!And'
    data_type = 'seq'

    # "Fn::And": [{condition}, {...}]

    @property
    def conditions(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Fn::And": self._data}, cls=DateTimeEncoder)


class Equals(AwsFnBase):
    yaml_tag = u'!Equals'
    data_type = 'seq'

    """
        "Fn::Equals" : ["value_1", "value_2"]
        YAML
        Syntax for the full function name:

        Fn::Equals: [value_1, value_2]
        Syntax for the short form:

        !Equals [value_1, value_2]
        """

    @property
    def value1(self):
        return self._data[0]

    @property
    def value2(self):
        return self._data[1]

    def __repr__(self):
        return json.dumps({"Fn::Equals": self._data}, cls=DateTimeEncoder)


class If(AwsFnBase):
    yaml_tag = u'!If'
    data_type = 'seq'

    @property
    def condition(self):
        return self._data[0]

    @property
    def if_true(self):
        return self._data[1]

    @property
    def if_false(self):
        return self._data[2]

    def __repr__(self):
        return json.dumps({"Fn::If": self._data}, cls=DateTimeEncoder)


class Not(AwsFnBase):
    yaml_tag = u'!Not'
    data_type = 'seq'

    @property
    def condition(self):
        return self._data[0]

    def __repr__(self):
        return json.dumps({"Fn::Not": self._data}, cls=DateTimeEncoder)


class Or(AwsFnBase):
    yaml_tag = u'!Or'
    data_type = 'seq'

    @property
    def conditions(self):
        return self._data

    def __repr__(self):
        return json.dumps({"Fn::Or": self._data}, cls=DateTimeEncoder)


if __name__ == "__main__":
    # note, whitespaces around the brackets & braces have been normalized so they
    # wouldn't produce false mismatches.    otherwise, ruamel does normalize the
    # spacing
    document = """
        TestBase64:
            Long:
                Fn::Base64: valueToEncode
            Short: !Base64 valueToEncode
        TestFindInMap:
            Long1:
                Fn::FindInMap: [MapName, TopLevelKey, SecondLevelKey]
            Long2:
                Fn::FindInMap:
                    - MapName
                    - TopLevelKey
                    - SecondLevelKey
            Short1: !FindInMap [Mapname, TopLevelKey, SecondLevelKey]
            Short2: !FindInMap
                - MapName
                - TopLevelKey
                - SecondLevelKey
        TestGetAtt:
            Long1:
                Fn::GetAtt: [logicalName, attributeName]
            Long2:
                Fn::GetAtt:
                    - logicalName
                    - attributeName
            Short: !GetAtt logicalName.attributeName
        TestGetAZs:
            Long:
                Fn::GetAZs: region
            Short: !GetAZs region
        TestImportValue:
            Long:
                Fn::ImportValue: sharedValueToImport
            Short: !ImportValue sharedValueToImport
        TestJoin:
            Long1:
                    Fn::Join: [delimiter, [comma, delimited, list, of, values]]
            Long2:
                    Fn::Join:
                        - delimiter
                        - [comma, delimited, list, of, values]
            Long3:
                    Fn::Join:
                        - delimiter
                        - - comma
                            - delimited
                            - list
                            - of
                            - values
            Short1: !Join [delimiter, [comma, delimited, list, of, values]]
            Short2: !Join
                - delimiter
                - [comma, delimited, list, of, values]
            Short3: !Join
                - delimiter
                - - comma
                    - delimited
                    - list
                    - of
                    - values
        TestSelect:
            Long1:
                    Fn::Select: [index, [list, of, objects]]
            Long2:
                    Fn::Select:
                        - index
                        - [list, of, objects]
            Long3:
                    Fn::Select:
                        - index
                        - - list
                            - of
                            - objects
            Short1: !Select [index, [list, of, objects]]
            Short2: !Select
                - index
                - [list, of, objects]
            Short3: !Select
                - index
                - - list
                    - of
                    - objects
        TestSplit:
            Long1:
                    Fn::Split: [delimiter, source]
            Long2:
                    Fn::Split:
                        - delimiter
                        - source
            Short1: !Split [delimiter, source]
            Short2: !Split
                - delimiter
                - source
        TestSub:
            Long1:
                Fn::Sub: [source, {Key1: Value1, Key2: Value2}]
            Long2:
                Fn::Sub:
                    - source
                    - {Key1: Value1, Key2: Value2}
            Long3:
                Fn::Sub:
                    - source
                    - Key1: Value1
                        Key2: Value2
            Long4:
                Fn::Sub: source
            Short1: !Sub [source, {Key1: Value1, Key2: Value2}]
            Short2: !Sub
                    - source
                    - {Key1: Value1, Key2: Value2}
            Short3: !Sub
                    - source
                    - Key1: Value1
                        Key2: Value2
            Short4: Sub! source
        TestRef:
            Long:
                Ref: logicalName
            Short: !Ref logicalName
        TestCondition:
            Short: !Condition Foo
        TestAnd:
            Long:
                Fn::And: [conditon1, condition2]
            Short: !And [condition, condition2]
            Examples:
                MyAndConition: !And
                    - !Equals [sg-mysgsgroup, !Ref ASecurityGroup]
                    - !Condition SomeOtherCondition
        TestEquals:
            Long:
                Fn::Equals: [value1, value2]
            Short: !Equals [value1, value2]
            Examples:
                UseProdCondition:
                    !Equals [!Ref EnvironmentType, prod]
        TestIf:
            Long:
                Fn::If: [condition_name, value_if_true, value_if_false]
            Short: !If [condition_name, value_if_true, value_if_false]
            Examples:
                SecurityGroups:
                    - !If [CreateNewSecurityGroup, !Ref NewSecurityGroup, !Ref ExistingSecurityGroup]
                SecurityGroupId:
                    Description: Group ID of the security group used.
                    Value: !If [CreateNewSecurityGroup, !Ref NewSecurityGroup, !Ref ExistingSecurityGroup]
                MyDB:
                    Type: "AWS::RDS::DBInstance"
                    Properties:
                        AllocatedStorage: 5
                        DBInstanceClass: db.m1.small
                        Engine: MySQL
                        EngineVersion: 5.5
                        MasterUsername: !Ref DBUser
                        MasterUserPassword: !Ref DBPassword
                        DBParameterGroupName: !Ref MyRDSParamGroup
                        DBSnapshotIdentifier:
                            !If [UseDBSnapshot, !Ref DBSnapshotName, !Ref "AWS::NoValue"]
                UpdatePolicy:
                    AutoScalingRollingUpdate:
                        !If
                            - RollingUpdates
                            -
                                MaxBatchSize: 2
                                MinInstancesInService: 2
                                PauseTime: PT0M30S
                            - !Ref "AWS::NoValue"
        TestNot:
            Long:
                Fn::Not: [condition]
            Short: !Not [condition]
            Examples:
                MyNotCondition:
                    !Not [!Equals [!Ref EnvironmentType, prod]]
        TestOr:
            Long:
                Fn::Or: [conditon1, condition2]
            Short: !Or [condition, condition2]
            Examples:
                MyOrConition:
                    !Or [!Equals [sg-mysgsgroup, !Ref ASecurityGroup], !Condition SomeOtherCondition]
        """

    #open('expected.yml', 'w').write(document)
    #result = ruamel.yaml.round_trip_dump(ruamel.yaml.round_trip_load(document, preserve_quotes=True), indent=4, block_seq_indent=2)
    #open('actual.yml', 'w').write(result)


def validate_template(template_data, region='us-east-1', profile='claytonbrown-admin'):

    #import tempfile
    #fp_yaml = tempfile.TemporaryFile()
    data = cfn_yaml(template_data).replace('\n', '')
    # fp_yaml.write(bytes(data.encode('utf-8')))
    # fp_yaml.close()
    #print("Saved YAML output: %s" % (fp_yaml))
    result = subprocess.run(['aws', 'cloudformation', 'validate-template', '--profile %s' % (profile), '--region %s' % (region), '--template-body %s' % (data)])
    print(result.stdout)

    #fp_json = tempfile.TemporaryFile()
    data = cfn_json(template_data).replace('\n', '')
    # fp_json.write(bytes(data.encode('utf-8')))
    # fp_json.close()
    #print("Saved JSON output: %s" % (fp_json))
    result = subprocess.run(['aws', 'cloudformation', 'validate-template', '--profile %s' % (profile), '--region %s' % (region), '--template-body %s' % (data)])
    print(result.stdout)

    return ''


def cfn_yaml(template_data):
    # return ruamel.yaml.dump(template_data)
    return ruamel.yaml.dump(template_data, Dumper=ruamel.yaml.RoundTripDumper)


def cfn_json(template_data):
    return cf_util.jsonprettyprint_template(template_data)


if __name__ == "__main__":
    import sys
    import cf_util
    # print("Reading in " + sys.argv[1])
    file_data = open(sys.argv[1], 'r').read()

    result = subprocess.run(['aws', 'cloudformation', 'validate-template', '--profile %s' % (profile), '--region %s' % (region), '--template-body %s' % (data)])
    print(result.stdout)

    template_data = ruamel.yaml.round_trip_load(file_data)

    # print(json.dumps(template_data, indent=4, sort_keys=True, cls=DateTimeEncoder))
    # validate_template(template_data)

    #print("vimdiff -c 'set diffopt+=iwhite' expected.yml actual.yml")
