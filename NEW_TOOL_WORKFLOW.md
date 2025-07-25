When Creating a new tool, follow this basic workflow for the most consistent task creation.

<workflow_before_talking_to_human>
1. setup
2. investigation
3. implementation
6. run `task pre-commit`
4. testing ensuring all tests pass and have no warnings when running `task test`
5. documentation
6. restart the ado-mcp server
7. exercise the new tool using your ado-mcp server tool
</workflow_before_talking_to_human>

<setup>
The repository root should have a .env file that contains environment variables for
* ADO_ORGANIZATION_URL
* AZURE_DEVOPS_EXT_PAT

These can be used to interact with Azure DevOps and should be automatically available when running any tasks in the taskfile.
</setup>

<investigation>
For the new feature find the docs for any relevant ADO Rest APIs from the microsoft Azure DevOps documentation
https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/?view=azure-devops-rest-7.2

After understanding the schema for the endpoints, try using curl to exercise the endpoint and better understand the data structure and flow
</investigation>

<implementation>
Once you understand the data structure 
1. create any new pydantic models we may need to parse a given response, or send a given request.
2. Create the new feature in the ado package
3. expose the new feature via a tool
</implementation>

<testing>
* Create an end to end test that will test the tool execution.
* Tests should be isolated from each other and able to run in parallel
* use curl or the ado python package we created to find test values such as project id and stuff to make the tests work.
</testing>

<documentation>
- Write **docstrings for every public function** using the Google style:
<example>
```python
def example():
  """
  Brief summary.

  Args:
      param1 (type): Description.

  Returns:
      type: Description.
  """
```
</example>

</documentation>