import com.microsoft.jenkins.containeragents.aci.AciCloud
import com.microsoft.jenkins.containeragents.builders.AciCloudBuilder
import com.microsoft.jenkins.containeragents.builders.AciContainerTemplateBuilder
import groovy.json.JsonSlurper
import java.time.Instant
import jenkins.model.Jenkins

def manifestPath = System.getenv("PLATFORM_BOOTSTRAP_MANIFEST")
if (manifestPath == null) {
    throw new IllegalArgumentException("PLATFORM_BOOTSTRAP_MANIFEST is required")
}
def manifestFile = new File(manifestPath)
if (!manifestFile.isFile()) {
    throw new IllegalArgumentException("reviewed bootstrap manifest does not exist")
}
def manifest = new JsonSlurper().parse(manifestFile)
if (manifest.schemaVersion != 1 || manifest.manifestStatus != "reviewed" ||
    manifest.state?.locked != true || manifest.identities?.validator != null ||
    manifest.identities?.ui != null ||
    !(manifest.identities?.publisher instanceof String) ||
    !(manifest.identities?.deployer instanceof String) ||
    manifest.identities.publisher == manifest.identities.deployer ||
    Instant.parse(manifest.review.expiresAt as String).isBefore(Instant.now())) {
    throw new IllegalStateException("fresh reviewed identityless-validator bootstrap manifest is required")
}

def publisherImage = System.getenv("PUBLISHER_IMAGE")
def deployerImage = System.getenv("DEPLOYER_IMAGE")
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
    .withResourceGroup(existing.resourceGroup)
    .withAzureLogAnalyticsCredentialsId(existing.logAnalyticsCredentialsId)
(retained + validator + [publisher, deployer]).each { replacement.addToTemplates(it) }

jenkins.clouds.remove(existing)
jenkins.clouds.add(replacement.build())
jenkins.save()
println("Configured reviewed-manifest-bound azure-aci-publisher and azure-aci-deployer templates")
