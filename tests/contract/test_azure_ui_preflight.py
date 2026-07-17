import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def source(path): return (ROOT / path).read_text()


def test_exact_locked_azurerm_azuread_providers_and_blob_state_contract():
    versions = source("infra/azure/versions.tf")
    lock = source("infra/azure/.terraform.lock.hcl")
    providers = source("infra/azure/providers.tf")
    backend = source("infra/azure/backend.tf")
    assert 'version = "~> 4.80"' in versions and 'version = "~> 3.6"' in versions
    assert 'version     = "4.81.0"' in lock and 'version     = "3.9.0"' in lock
    assert 'provider "azurerm"' in providers and 'provider "azuread"' in providers
    assert 'resource_provider_registrations = "none"' in providers
    assert 'backend "azurerm"' in backend and "use_azuread_auth = true" in backend
    assert "Azure Blob leases provide locking" in backend


def test_jit_platform_scopes_separate_graph_consent_and_negative_privilege_are_fail_closed():
    bootstrap = source("scripts/azure/bootstrap-ui-platform.sh")
    for scope in (
        "Application Administrator", "Contributor:application-rg", "Network Contributor:named-shared-network",
        "Private DNS Zone Contributor:named-zones", "ProviderQuotaRead:allowlisted",
        "Role Based Access Control Administrator:application-rg", "Storage Blob Data Contributor:state-container",
    ):
        assert scope in bootstrap
    assert 'role=="Privileged Role Administrator"' in bootstrap
    assert ".consentApprover.objectId!=.actorObjectId" in bootstrap
    for denied in ("Global Administrator", "Owner", "Jenkins principal", "standing privilege", "unrelated app/data/resource access"):
        assert denied in bootstrap
    assert 'parse(auth["activatedAt"]) <= now < parse(auth["expiresAt"])' in bootstrap
    assert "timedelta(days=7)" in bootstrap


def test_only_finalizer_can_emit_reviewed_manifest_after_state_identity_alb_migration_and_denial_attestations():
    bootstrap = source("scripts/azure/bootstrap-ui-platform.sh")
    data = source("scripts/azure/bootstrap-data-principals.sh")
    finalizer = source("scripts/azure/finalize-ui-platform.sh")
    assert "no environment-manifest write" in bootstrap
    assert "platform-bootstrap-nonprod.json" not in data
    assert 'PLATFORM_FINALIZATION_AUTHORIZED:-}" == T194' in finalizer
    for key in ("albController", "identityDenials", "jitPermissions", "migrationPolicy", "providerQuotaCapacity"):
        assert key in finalizer
    assert '.locked==true' in finalizer and "timedelta(days=7)" in finalizer
    assert "preflight-ui-platform.sh\" live" in finalizer
    assert 'chmod 0444 "$temporary"' in finalizer


def test_canonical_configuration_policy_includes_platform_inputs_and_excludes_state_runtime_secrets_and_emitted_manifest():
    policy = json.loads(source("config/platform-configuration-digest-v1.yaml"))
    assert policy["algorithm"] == "sha256-canonical-path-mode-length-content-v1"
    for included in ("infra/azure/*.tf", "infra/azure/.terraform.lock.hcl", "deploy/k8s/**/*.yaml", "scripts/azure/*.sh"):
        assert included in policy["includes"]
    for excluded in (
        "config/platform-bootstrap-nonprod.json", "**/.terraform/**", "**/.git/**", "**/*.tfstate",
        "**/*.tfplan", "**/terraform.tfvars", "**/.env*", "**/*.secret.*", "**/secrets/**",
        "**/*kubeconfig*", "**/evidence/**", "**/runtime/**",
    ):
        assert excluded in policy["excludes"]
    digest = source("scripts/azure/compute-platform-configuration-digest.sh")
    assert "sorted(files)" in digest and '"path"' in digest and '"mode"' in digest and '"length"' in digest and '"sha256"' in digest


def test_canonical_digest_detects_add_remove_rename_mode_and_content_drift(tmp_path):
    repo = tmp_path / "repo"; (repo / "config").mkdir(parents=True); (repo / "tracked").mkdir()
    script = ROOT / "scripts/azure/compute-platform-configuration-digest.sh"
    policy = {"schemaVersion": 1, "algorithm": "sha256-canonical-path-mode-length-content-v1", "includes": ["tracked/*"], "excludes": []}
    policy_path = repo / "config/policy.json"; policy_path.write_text(json.dumps(policy))
    item = repo / "tracked/item.txt"; item.write_text("one")
    def digest():
        result = subprocess.run([str(script), str(repo), str(policy_path)], text=True, capture_output=True, check=True)
        return json.loads(result.stdout)["digest"]
    baseline = digest(); item.write_text("two"); content = digest(); item.chmod(0o755); mode = digest()
    renamed = repo / "tracked/renamed.txt"; item.rename(renamed); rename = digest()
    added = repo / "tracked/added.txt"; added.write_text("added"); add = digest(); added.unlink(); remove = digest()
    assert len({baseline, content, mode, rename, add}) == 5
    assert remove == rename and remove != add


def test_preflight_denies_jenkins_terraform_state_and_requires_aks_gateway_acr_capacity_and_target_rg_reader_contracts():
    preflight = source("scripts/azure/preflight-ui-platform.sh")
    identities = source("infra/azure/jenkins-agent-identities.tf")
    main = source("infra/azure/main.tf")
    agc = source("infra/azure/application-gateway-for-containers.tf")
    assert 'terraformStateRead:false' in preflight and 'subscriptionWideRead:false' in preflight
    assert "terraform-state" in identities and "target-rg-reader" in identities
    assert "oidc_issuer_enabled" in main and "workload_identity_enabled" in main
    assert 'role_definition_name = "AcrPull"' in main
    assert "gateway_api_version" in agc and "minimum_kubernetes_version" in agc
    assert "providerQuotaCapacity" in source("config/platform-bootstrap.schema.json")
