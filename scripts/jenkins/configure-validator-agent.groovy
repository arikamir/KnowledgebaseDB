import com.microsoft.jenkins.containeragents.aci.AciCloud
import com.microsoft.jenkins.containeragents.builders.AciCloudBuilder
import com.microsoft.jenkins.containeragents.builders.AciContainerTemplateBuilder
import jenkins.model.Jenkins

def setting = { String name ->
    System.getenv(name) ?: System.getProperty("knowledgebasedb.${name}")
}
def image = setting("VALIDATOR_IMAGE")
if (image == null || !(image ==~ /[^\s@]+@sha256:[0-9a-f]{64}/)) {
    throw new IllegalArgumentException(
        "VALIDATOR_IMAGE must be an immutable repository@sha256:<64 lowercase hex> reference"
    )
}

def jenkins = Jenkins.get()
def existing = jenkins.clouds.getByName("azure")
if (!(existing instanceof AciCloud)) {
    throw new IllegalStateException("The preconfigured Jenkins ACI cloud 'azure' is required")
}

def retainedTemplates = existing.templates.findAll {
    it.name != "azure-aci-validator" && it.label != "azure-aci-validator"
}

def validator = new AciContainerTemplateBuilder()
    .withName("azure-aci-validator")
    .withLabel("azure-aci-validator")
    .withImage(image)
    .withOsType("Linux")
    .withRootFs("/home/jenkins")
    .withTimeout(15)
    .withCpu("2")
    .withMemory("4")
    .withEnvVars([])
    .withPorts([])
    .withVolume([])
    .withOnceRetentionStrategy()
    .withJNLPLaunchMethod()
    .build()

def replacementBuilder = new AciCloudBuilder()
    .withCloudName(existing.name)
    .withAzureCredentialsId(existing.credentialsId)
    .withResourceGroup(existing.resourceGroup)
    .withAzureLogAnalyticsCredentialsId(existing.logAnalyticsCredentialsId)

(retainedTemplates + validator).each { replacementBuilder.addToTemplates(it) }

jenkins.clouds.remove(existing)
jenkins.clouds.add(replacementBuilder.build())
jenkins.save()

println("Configured pinned one-shot azure-aci-validator template")
