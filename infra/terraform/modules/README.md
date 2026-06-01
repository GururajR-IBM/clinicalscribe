# Modules

Composition modules wrapping Azure Verified Modules (AVM). Filled in by phase:

| Module          | Phase | Purpose                                                |
| --------------- | ----- | ------------------------------------------------------ |
| `network`       | 1     | VNet, subnets (AKS, PE, APIM), NSGs, optional firewall |
| `aks`           | 1     | AKS cluster, workload identity, OIDC, Azure CNI Overlay |
| `data`          | 1     | Cosmos NoSQL, Postgres Flex, Blob, Key Vault            |
| `messaging`     | 2     | Service Bus namespace, queues                           |
| `ai`            | 2-3   | Azure OpenAI, Speech, Doc Intel, Content Safety         |
| `search`        | 3     | AI Search Basic + vector + semantic config              |
| `observability` | 1     | Log Analytics, App Insights, alerts                     |
| `apim`          | 6     | API Management Consumption tier + AI gateway policies   |
