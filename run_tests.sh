#!/bin/bash

export ADO_PAT=$(security find-generic-password -w -a ado-token)
export ADO_ORGANIZATION_URL="https://dev.azure.com/RussellBoley"

uv run pytest
