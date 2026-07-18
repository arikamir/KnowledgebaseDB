import com.microsoft.jenkins.containeragents.aci.AciCloud
import com.microsoft.jenkins.containeragents.builders.AciCloudBuilder
import com.microsoft.jenkins.containeragents.builders.AciContainerTemplateBuilder
import groovy.json.JsonSlurper
import java.time.Instant
import jenkins.model.Jenkins

def setting = { String name ->
    System.getenv(name) ?: System.getProperty("knowledgebasedb.${name}")
}
def manifestPath = setting("PLATFORM_BOOTSTRAP_MANIFEST")
if (manifestPath == null) {
    throw new IllegalArgumentException("PLATFORM_BOOTSTRAP_MANIFEST is required")
}
def manifestFile = new File(manifestPath)
if (!manifestFile.isFile()) {
    throw new IllegalArgumentException("reviewed bootstrap manifest does not exist")
}
def manifest = new JsonSlurper().parse(manifestFile)
def subscriptionId = manifest.subscriptionId as String
def resourceGroup = manifest.resourceGroup as String
def identityPrefix = "/subscriptions/${subscriptionId}/resourceGroups/${resourceGroup}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/"
def allowTechnicalPoc = setting("ALLOW_TECHNICAL_POC") == "true"
def acceptedStatus = manifest.manifestStatus == "reviewed" ||
    (allowTechnicalPoc && manifest.manifestStatus == "poc-reviewed" &&
     manifest.attestations?.jitPermissions?.formalT194 == false &&
     manifest.attestations?.identityDenials?.formalT194 == false)
if (manifest.schemaVersion != 1 || !acceptedStatus ||
    manifest.state?.locked != true || manifest.identities?.validator != null ||
    manifest.identities?.ui != null ||
    !(subscriptionId ==~ /[0-9a-fA-F-]{36}/) ||
    !(resourceGroup ==~ /rg-[a-z0-9-]+/) ||
    !(manifest.identities?.publisher instanceof String) ||
    !(manifest.identities?.deployer instanceof String) ||
    !manifest.identities.publisher.startsWith(identityPrefix) ||
    !manifest.identities.deployer.startsWith(identityPrefix) ||
    manifest.identities.publisher == manifest.identities.deployer ||
    Instant.parse(manifest.review.expiresAt as String).isBefore(Instant.now())) {
    throw new IllegalStateException("fresh reviewed identityless-validator bootstrap manifest is required")
}

def publisherImage = setting("PUBLISHER_IMAGE")
def deployerImage = setting("DEPLOYER_IMAGE")
[publisherImage, deployerImage].each { image ->
    if (image == null || !(image ==~ /[^\s@]+@sha256:[0-9a-f]{64}/)) {
        throw new IllegalArgumentException("publisher and deployer images must be immutable digest references")
    }
}

def jenkins = Jenkins.get()
def existing = jenkins.clouds.getByName("azure")
if (!(existing instanceof AciCloud)) {
    throw new IllegalStateException("The preconfigured Jenkins ACI cloud 'azure' is required")
}
def validator = existing.templates.findAll {
    it.name == "azure-aci-validator" && it.label == "azure-aci-validator"
}
if (validator.size() != 1) {
    throw new IllegalStateException("exactly one preconfigured identityless validator is required")
}

def capabilityProbe = new AciContainerTemplateBuilder()
if (capabilityProbe.metaClass.respondsTo(
        capabilityProbe, "withUseSystemAssignedIdentity", Boolean.TYPE).isEmpty() ||
    capabilityProbe.metaClass.respondsTo(
        capabilityProbe, "withUserAssignedIdentities", List).isEmpty()) {
    throw new UnsupportedOperationException(
        "installed azure-container-agents plugin cannot attach exact ACI managed identities"
    )
}

def deliveryTemplate = { String name, String image, String identity ->
    new AciContainerTemplateBuilder()
        .withName(name)
        .withLabel(name)
        .withImage(image)
        .withOsType("Linux")
        .withRootFs("/home/jenkins")
        .withTimeout(15)
        .withCpu("2")
        .withMemory("4")
        .withEnvVars([])
        .withPorts([])
        .withVolume([])
        .withUseSystemAssignedIdentity(false)
        .withUserAssignedIdentities([identity])
        .withOnceRetentionStrategy()
        .withJNLPLaunchMethod()
        .build()
}

def publisher = deliveryTemplate(
    "azure-aci-publisher", publisherImage, manifest.identities.publisher as String
)
def deployer = deliveryTemplate(
    "azure-aci-deployer", deployerImage, manifest.identities.deployer as String
)
def retained = existing.templates.findAll {
    !(it.name in ["azure-aci-validator", "azure-aci-publisher", "azure-aci-deployer"])
}
def replacement = new AciCloudBuilder()
    .withCloudName(existing.name)
    .withAzureCredentialsId(existing.credentialsId)
    // The reviewed manifest is authoritative. This also prevents a controller
    // retained from an earlier region from provisioning delivery agents there.
    .withResourceGroup(resourceGroup)
    .withAzureLogAnalyticsCredentialsId(existing.logAnalyticsCredentialsId)
(retained + validator + [publisher, deployer]).each { replacement.addToTemplates(it) }

jenkins.clouds.remove(existing)
jenkins.clouds.add(replacement.build())
jenkins.save()
println("Configured reviewed-manifest-bound azure-aci-publisher and azure-aci-deployer templates")
