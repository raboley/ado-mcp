ADO MCP Documentation
=====================

Welcome to the ADO MCP documentation! This is an MCP (Model Context Protocol) server that provides Azure DevOps integration for AI assistants and development tools.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   api
   examples
   troubleshooting

Overview
--------

ADO MCP enables your AI assistant to:

* List projects and pipelines in your Azure DevOps organization
* Run pipelines and monitor their status
* Analyze build failures and view detailed logs
* Troubleshoot pipeline issues with intelligent failure analysis
* Access build artifacts and timeline information

Quick Start
-----------

1. Install UV and Azure CLI
2. Authenticate with Azure DevOps using ``az devops login``
3. Add the MCP server to your AI assistant using ``uvx ado-mcp-raboley``

See the :doc:`installation` guide for detailed instructions.

Features
--------

Pipeline Operations
~~~~~~~~~~~~~~~~~~~
* List and manage pipelines
* Run pipelines with real-time monitoring
* Get detailed pipeline information
* Access build results and artifacts

Smart Analysis
~~~~~~~~~~~~~~
* Intelligent failure analysis with root cause detection
* Step-by-step log analysis
* Timeline visualization
* Performance insights

Flexible Authentication
~~~~~~~~~~~~~~~~~~~~~~~
* Azure CLI integration (recommended)
* Personal Access Token support
* Multiple authentication fallbacks
* Secure credential storage

Performance & Caching
~~~~~~~~~~~~~~~~~~~~~~
* Intelligent caching for fast lookups
* Automatic cache invalidation
* Batch operations support
* MCP resource optimization

API Reference
-------------

.. autosummary::
   :toctree: _autosummary
   :recursive:

   ado

.. toctree::
   :hidden:

   _autosummary/ado.cache
   _autosummary/ado.client
   _autosummary/ado.errors
   _autosummary/ado.helpers
   _autosummary/ado.lookups
   _autosummary/ado.models
   _autosummary/ado.pipelines
   _autosummary/ado.pipelines.builds
   _autosummary/ado.pipelines.logs
   _autosummary/ado.pipelines.pipelines
   _autosummary/ado.resources
   _autosummary/ado.rst
   _autosummary/ado.tools

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`