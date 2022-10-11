import json

doc = """{
  "AWSTemplateFormatVersion" : "version date",

  "Description" : "JSON string",

  "Metadata" : {
    
  },

  "Parameters" : {
  },
  
  "Rules" : {
  },

  "Mappings" : {
  },

  "Conditions" : {
  },

  "Transform" : {
  },

  "Resources" : {
  },
  
  "Outputs" : {
  }
}"""

data = json.loads(doc)
print(json.dumps(data, indent=4, sort_keys=True))