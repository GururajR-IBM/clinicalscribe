"""Blob Storage helpers for the gateway.

In production: uses Azure Blob Storage SAS token generation.
In local dev: returns a fake URL so the service starts without real Azure creds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gateway.config import settings


async def generate_upload_sas_url(
    blob_name: str,
    content_type: str,
    ttl_minutes: int = 15,
) -> tuple[str, datetime]:
    """Return (signed_upload_url, expires_at).

    When AZURE_STORAGE_CONNECTION_STRING is set we generate a real SAS URL.
    Otherwise we return a local placeholder so routes work end-to-end without
    Azure credentials (useful for unit tests and local dev).
    """
    expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

    if not settings.azure_storage_connection_string:
        # Local dev / test mode
        fake_url = (
            f"http://127.0.0.1:10000/devstoreaccount1/"
            f"{settings.azure_storage_container_encounter_media}/{blob_name}"
        )
        return fake_url, expires_at

    # Production: generate a real SAS URL using azure-storage-blob
    from azure.storage.blob import (
        BlobSasPermissions,
        BlobServiceClient,
        generate_blob_sas,
    )

    service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    account_name = service.account_name
    account_key = service.credential.account_key  # only used for SAS signing

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=settings.azure_storage_container_encounter_media,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=expires_at,
        content_type=content_type,
    )

    url = (
        f"https://{account_name}.blob.core.windows.net/"
        f"{settings.azure_storage_container_encounter_media}/{blob_name}?{sas_token}"
    )
    return url, expires_at
