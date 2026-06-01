# ingestion-worker

Service Bus-driven background worker. Per encounter: pull audio + scans from Blob, run ASR (Azure Speech), OCR (Document Intelligence), chunk + embed, write evidence to Cosmos.

**Phase:** stub in Phase 0; implemented in Phase 2.
