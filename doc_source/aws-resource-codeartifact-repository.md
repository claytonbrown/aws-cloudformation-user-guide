# AWS::CodeArtifact::Repository<a name="aws-resource-codeartifact-repository"></a>

The `AWS::CodeArtifact::Repository` resource creates an AWS CodeArtifact repository\. CodeArtifact *repositories* contain a set of package versions\. For more information about repositories, see the [Repository concepts information](https://docs.aws.amazon.com/codeartifact/latest/ug/codeartifact-concepts.html#welcome-concepts-repository) in the *CodeArtifact User Guide*\. For more information about the `CreateRepository` API, see [CreateRepository](https://docs.aws.amazon.com/codeartifact/latest/APIReference/API_CreateRepository.html) in the *CodeArtifact API Reference*\.

## Syntax<a name="aws-resource-codeartifact-repository-syntax"></a>

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON<a name="aws-resource-codeartifact-repository-syntax.json"></a>

```
{
  "Type" : "AWS::CodeArtifact::Repository",
  "Properties" : {
      "[Description](#cfn-codeartifact-repository-description)" : String,
      "[DomainName](#cfn-codeartifact-repository-domainname)" : String,
      "[DomainOwner](#cfn-codeartifact-repository-domainowner)" : String,
      "[ExternalConnections](#cfn-codeartifact-repository-externalconnections)" : [ String, ... ],
      "[PermissionsPolicyDocument](#cfn-codeartifact-repository-permissionspolicydocument)" : Json,
      "[RepositoryName](#cfn-codeartifact-repository-repositoryname)" : String,
      "[Upstreams](#cfn-codeartifact-repository-upstreams)" : [ String, ... ]
    }
}
```

### YAML<a name="aws-resource-codeartifact-repository-syntax.yaml"></a>

```
Type: AWS::CodeArtifact::Repository
Properties: 
  [Description](#cfn-codeartifact-repository-description): String
  [DomainName](#cfn-codeartifact-repository-domainname): String
  [DomainOwner](#cfn-codeartifact-repository-domainowner): String
  [ExternalConnections](#cfn-codeartifact-repository-externalconnections): 
    - String
  [PermissionsPolicyDocument](#cfn-codeartifact-repository-permissionspolicydocument): Json
  [RepositoryName](#cfn-codeartifact-repository-repositoryname): String
  [Upstreams](#cfn-codeartifact-repository-upstreams): 
    - String
```

## Properties<a name="aws-resource-codeartifact-repository-properties"></a>

`Description`  <a name="cfn-codeartifact-repository-description"></a>
 A text description of the repository\.   
*Required*: No  
*Type*: String  
*Maximum*: `1000`  
*Pattern*: `\P{C}+`  
*Update requires*: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

`DomainName`  <a name="cfn-codeartifact-repository-domainname"></a>
 The name of the domain that contains the repository\.   
*Required*: Yes  
*Type*: String  
*Minimum*: `2`  
*Maximum*: `50`  
*Pattern*: `[a-z][a-z0-9\-]{0,48}[a-z0-9]`  
*Update requires*: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)

`DomainOwner`  <a name="cfn-codeartifact-repository-domainowner"></a>
 The 12\-digit account number of the AWS account that owns the domain that contains the repository\. It does not include dashes or spaces\.   
*Required*: No  
*Type*: String  
*Minimum*: `12`  
*Maximum*: `12`  
*Pattern*: `[0-9]{12}`  
*Update requires*: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)

`ExternalConnections`  <a name="cfn-codeartifact-repository-externalconnections"></a>
 An array of external connections associated with the repository\.   
*Required*: No  
*Type*: List of String  
*Update requires*: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

`PermissionsPolicyDocument`  <a name="cfn-codeartifact-repository-permissionspolicydocument"></a>
The document that defines the resource policy that is set on a repository\.  
*Required*: No  
*Type*: Json  
*Update requires*: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

`RepositoryName`  <a name="cfn-codeartifact-repository-repositoryname"></a>
 The name of an upstream repository\.   
*Required*: Yes  
*Type*: String  
*Minimum*: `2`  
*Maximum*: `100`  
*Pattern*: `[A-Za-z0-9][A-Za-z0-9._\-]{1,99}`  
*Update requires*: [Replacement](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-replacement)

`Upstreams`  <a name="cfn-codeartifact-repository-upstreams"></a>
 A list of upstream repositories to associate with the repository\. The order of the upstream repositories in the list determines their priority order when AWS CodeArtifact looks for a requested package version\. For more information, see [Working with upstream repositories](https://docs.aws.amazon.com/codeartifact/latest/ug/repos-upstream.html)\.   
*Required*: No  
*Type*: List of String  
*Update requires*: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

## Return values<a name="aws-resource-codeartifact-repository-return-values"></a>

### Ref<a name="aws-resource-codeartifact-repository-return-values-ref"></a>

When you pass the logical ID of this resource to the intrinsic `Ref` function, `Ref` returns the resource arn\.

### Fn::GetAtt<a name="aws-resource-codeartifact-repository-return-values-fn--getatt"></a>

The `Fn::GetAtt` intrinsic function returns a value for a specified attribute of this type\. The following are the available attributes and sample return values\.

For more information about using the `Fn::GetAtt` intrinsic function, see [Fn::GetAtt](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html)\.

#### <a name="aws-resource-codeartifact-repository-return-values-fn--getatt-fn--getatt"></a>

`Arn`  <a name="Arn-fn::getatt"></a>
When you pass the logical ID of this resource, the function returns the Amazon Resource Name \(ARN\) of the repository\. 

`DomainName`  <a name="DomainName-fn::getatt"></a>
When you pass the logical ID of this resource, the function returns the domain name that contains the repository\.

`DomainOwner`  <a name="DomainOwner-fn::getatt"></a>
When you pass the logical ID of this resource, the function returns the 12\-digit account number of the AWS account that owns the domain that contains the repository\.

`Name`  <a name="Name-fn::getatt"></a>
When you pass the logical ID of this resource, the function returns the name of the repository\.