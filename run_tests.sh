#!/bin/bash

export AZURE_DEVOPS_EXT_PAT=$(security find-generic-password -w -a ado-token)
export ADO_ORGANIZATION_URL="https://dev.azure.com/RussellBoley"
export ADO_PROJECT_NAME="Learning"
export ADO_PIPELINE_ID="9"

uv run pytest