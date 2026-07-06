"""Pydantic models mirroring ``config/schema.yaml`` exactly.

This is the executable equivalent of the JSON Schema documented in
``docs/CONFIGURATION.md`` - the two must be kept in sync, the same way
``docs/CLI.md``'s field-reference tables are kept in sync with
``config/schema.yaml`` itself. If a field, default, or constraint is
added to the schema, add it here too, in the same shape.

``spec`` and the document root both allow ``x-``-prefixed extension keys
(see ``docs/CONFIGURATION.md#extensibility-model``); this is implemented
via ``extra="allow"`` plus a model validator that rejects any extra key
that is *not* ``x-``-prefixed, so the Pydantic model enforces exactly
what ``config/schema.yaml``'s ``patternProperties: "^x-"`` does.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bcs.model_utils import reject_non_x_extra

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ACADEMIC_YEAR = re.compile(r"^[0-9]{4}-[0-9]{4}$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_MAC = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class StrictModel(BaseModel):
    """Base for models with no extension points: extra keys are rejected."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExtensibleModel(BaseModel):
    """Base for models where only ``x-``-prefixed extra keys are allowed."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="after")
    def _check_extra(self) -> ExtensibleModel:
        reject_non_x_extra(self)
        return self


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------


class Metadata(StrictModel):
    name: Annotated[str, Field(pattern=_SLUG.pattern)]
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# spec.project
# ---------------------------------------------------------------------------


class ProjectSpec(StrictModel):
    display_name: str = Field(alias="displayName")
    centre: str
    academic_year: Annotated[
        str | None, Field(alias="academicYear", pattern=_ACADEMIC_YEAR.pattern)
    ] = None
    contact: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# spec.branding
# ---------------------------------------------------------------------------


class Colors(StrictModel):
    primary: Annotated[str | None, Field(pattern=_HEX_COLOR.pattern)] = None
    accent: Annotated[str | None, Field(pattern=_HEX_COLOR.pattern)] = None


class BrandingSpec(StrictModel):
    logo: str | None = None
    icon: str | None = None
    background: str | None = None
    font: str | None = None
    colors: Colors | None = None


# ---------------------------------------------------------------------------
# spec.bootManager
# ---------------------------------------------------------------------------


class MenuEntry(StrictModel):
    id: str
    label: dict[str, str] = Field(min_length=1)
    action: Literal["boot-installed-os", "request-deploy-maintenance", "boot-recovery"]


class Menu(StrictModel):
    timeout_seconds: Annotated[int, Field(alias="timeoutSeconds", ge=0)] = 10
    default_entry: str = Field(alias="defaultEntry")
    entries: list[MenuEntry] = Field(min_length=1)


class Fallback(StrictModel):
    on_config_error: Literal["boot-installed-os"] = Field(
        alias="onConfigError", default="boot-installed-os"
    )


class BootManagerSpec(StrictModel):
    enabled: bool = True
    menu: Menu
    fallback: Fallback = Field(default_factory=Fallback)


# ---------------------------------------------------------------------------
# spec.builder
# ---------------------------------------------------------------------------


class BaseImage(StrictModel):
    distro: Literal["lliurex"]
    distro_version: Annotated[str, Field(alias="distroVersion")] = "23"
    base_distribution: Literal["ubuntu"] = Field(alias="baseDistribution")
    base_distribution_version: Annotated[str, Field(alias="baseDistributionVersion")] = "24.04"
    pinned_snapshot: Annotated[str | None, Field(alias="pinnedSnapshot", pattern=_DATE.pattern)] = (
        None
    )


class RecoveryPartition(StrictModel):
    enabled: bool = True
    size_mi_b: Annotated[int, Field(alias="sizeMiB", ge=1024)] = 8192


class Partitioning(StrictModel):
    scheme: Literal["gpt"] = "gpt"
    esp_size_mi_b: Annotated[int, Field(alias="espSizeMiB", ge=256)] = 512
    recovery_partition: Annotated[RecoveryPartition, Field(alias="recoveryPartition")] = Field(
        default_factory=RecoveryPartition
    )


class Provenance(StrictModel):
    checksum_algorithm: Literal["sha256", "sha512"] = Field(
        alias="checksumAlgorithm", default="sha256"
    )


class BuildOutput(StrictModel):
    format: Literal["partclone"] = "partclone"
    compression: Literal["none", "gzip", "zstd"] = "zstd"


class BuilderSpec(StrictModel):
    base_image: Annotated[BaseImage, Field(alias="baseImage")]
    partitioning: Partitioning
    provenance: Provenance = Field(default_factory=Provenance)
    output: BuildOutput = Field(default_factory=BuildOutput)


# ---------------------------------------------------------------------------
# spec.packages
# ---------------------------------------------------------------------------


class Repository(StrictModel):
    name: str
    uri: str
    signing_key: str = Field(alias="signingKey")


class PackagesSpec(StrictModel):
    base: list[str] = Field(min_length=1)
    profiles: dict[str, list[str]] = Field(default_factory=dict)
    remove: list[str] = Field(default_factory=list)
    repositories: list[Repository] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# spec.deploy
# ---------------------------------------------------------------------------


class Pxe(StrictModel):
    enabled: bool = True
    server_address: Annotated[str | None, Field(alias="serverAddress")] = None


class Multicast(StrictModel):
    enabled: bool = True
    address_range: Annotated[str, Field(alias="addressRange")] = "232.10.10.0/24"


class Transport(StrictModel):
    pxe: Pxe = Field(default_factory=Pxe)
    multicast: Multicast = Field(default_factory=Multicast)


class Retry(StrictModel):
    max_attempts: Annotated[int, Field(alias="maxAttempts", ge=0)] = 3
    backoff_seconds: Annotated[int, Field(alias="backoffSeconds", ge=0)] = 30


class Session(StrictModel):
    reference_classroom_size: Annotated[int, Field(alias="referenceClassroomSize", ge=1)] = 30
    timeout_minutes: Annotated[int, Field(alias="timeoutMinutes", ge=1)] = 50
    retry: Retry = Field(default_factory=Retry)


class Verification(StrictModel):
    checksum_algorithm: Literal["sha256", "sha512"] = Field(
        alias="checksumAlgorithm", default="sha256"
    )
    on_mismatch: Literal["abort-machine", "abort-session"] = Field(
        alias="onMismatch", default="abort-machine"
    )


class Reporting(StrictModel):
    format: Literal["json", "text"] = "json"
    retention_days: Annotated[int, Field(alias="retentionDays", ge=1)] = 90


class MaintenanceRequests(StrictModel):
    enabled: bool = True
    machine_identity: Literal["mac-address", "dmi-uuid", "custom"] = Field(
        alias="machineIdentity", default="mac-address"
    )


class DeploySpec(StrictModel):
    transport: Transport = Field(default_factory=Transport)
    session: Session = Field(default_factory=Session)
    verification: Verification = Field(default_factory=Verification)
    reporting: Reporting = Field(default_factory=Reporting)
    maintenance_requests: Annotated[MaintenanceRequests, Field(alias="maintenanceRequests")] = (
        Field(default_factory=MaintenanceRequests)
    )


# ---------------------------------------------------------------------------
# spec.users
# ---------------------------------------------------------------------------


class DefaultProfile(StrictModel):
    shell: str = "/bin/bash"
    groups: list[str] = Field(default_factory=list)


class Account(StrictModel):
    name: Annotated[str, Field(pattern=r"^[a-z_][a-z0-9_-]*$")]
    role: Literal["teacher", "student", "technician"]
    groups: list[str] = Field(default_factory=list)
    sudo: bool = False


class Ldap(StrictModel):
    uri: str | None = None
    base_dn: str | None = Field(alias="baseDn", default=None)


class Authentication(StrictModel):
    method: Literal["local", "ldap", "none"] = "local"
    ldap: Ldap | None = None


class UsersSession(StrictModel):
    autologin: bool = False
    guest_session: bool = Field(alias="guestSession", default=True)


class UsersSpec(StrictModel):
    default_profile: Annotated[DefaultProfile, Field(alias="defaultProfile")] = Field(
        default_factory=DefaultProfile
    )
    accounts: list[Account] = Field(default_factory=list)
    authentication: Authentication = Field(default_factory=Authentication)
    session: UsersSession = Field(default_factory=UsersSession)


# ---------------------------------------------------------------------------
# spec.network
# ---------------------------------------------------------------------------


class Proxy(StrictModel):
    http: str | None = None
    https: str | None = None
    no_proxy: list[str] = Field(alias="noProxy", default_factory=list)


class StaticAssignment(StrictModel):
    hostname: str
    mac: Annotated[str, Field(pattern=_MAC.pattern)]
    ip: str


class Addressing(StrictModel):
    mode: Literal["dhcp", "static"] = "dhcp"
    static_assignments: Annotated[list[StaticAssignment], Field(alias="staticAssignments")] = Field(
        default_factory=list
    )


class NetworkSpec(StrictModel):
    hostname_pattern: Annotated[str, Field(alias="hostnamePattern")] = "{centre}-pc{index}"
    domain: str | None = None
    dns: list[str] = Field(default_factory=list)
    proxy: Proxy | None = None
    addressing: Addressing = Field(default_factory=Addressing)


# ---------------------------------------------------------------------------
# spec.localization
# ---------------------------------------------------------------------------


Locale = Literal["ca_ES", "es_ES", "en_US"]


def _default_supported_locales() -> list[Locale]:
    return ["ca_ES", "es_ES"]


class LocalizationSpec(StrictModel):
    default_locale: Literal["ca_ES", "es_ES"] = Field(alias="defaultLocale", default="ca_ES")
    supported_locales: Annotated[list[Locale], Field(alias="supportedLocales")] = Field(
        default_factory=_default_supported_locales
    )
    timezone: str = "Europe/Madrid"
    keyboard_layout: str = Field(alias="keyboardLayout", default="es")


# ---------------------------------------------------------------------------
# spec.security
# ---------------------------------------------------------------------------


class SecureBoot(StrictModel):
    mode: Literal["enforce", "permissive", "disabled"] = "enforce"


class Credentials(StrictModel):
    embed_shared_credentials: Literal[False] = Field(alias="embedSharedCredentials", default=False)


class Updates(StrictModel):
    auto_security_updates: bool = Field(alias="autoSecurityUpdates", default=True)


class ImageSigning(StrictModel):
    enabled: bool = False
    key_ref: str | None = Field(alias="keyRef", default=None)


class NetworkTrust(StrictModel):
    allowed_deploy_servers: list[str] = Field(alias="allowedDeployServers", default_factory=list)


class SecuritySpec(StrictModel):
    secure_boot: Annotated[SecureBoot, Field(alias="secureBoot")] = Field(
        default_factory=SecureBoot
    )
    credentials: Credentials = Field(default_factory=Credentials)
    updates: Updates = Field(default_factory=Updates)
    image_signing: Annotated[ImageSigning, Field(alias="imageSigning")] = Field(
        default_factory=ImageSigning
    )
    network_trust: Annotated[NetworkTrust, Field(alias="networkTrust")] = Field(
        default_factory=NetworkTrust
    )


# ---------------------------------------------------------------------------
# spec (top level) and the document envelope
# ---------------------------------------------------------------------------


class ClassroomSpec(ExtensibleModel):
    project: ProjectSpec
    branding: BrandingSpec | None = None
    boot_manager: Annotated[BootManagerSpec, Field(alias="bootManager")]
    builder: BuilderSpec
    packages: PackagesSpec
    deploy: DeploySpec
    users: UsersSpec | None = None
    network: NetworkSpec
    localization: LocalizationSpec
    security: SecuritySpec
    extensions: dict[str, object] = Field(default_factory=dict)


class ClassroomConfig(ExtensibleModel):
    """The executable equivalent of ``config/schema.yaml``'s root object."""

    api_version: Literal["bcs/v1alpha1"] = Field(alias="apiVersion")
    kind: Literal["ClassroomConfig"]
    metadata: Metadata
    spec: ClassroomSpec


__all__ = ["ClassroomConfig", "ClassroomSpec", "Metadata"]
