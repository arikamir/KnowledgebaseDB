import jenkins.model.Jenkins
import java.security.MessageDigest
import java.util.jar.JarFile

def setting = { String name -> System.getenv(name) ?: System.getProperty("knowledgebasedb.${name}") }
def hpiPath = setting("AZURE_CONTAINER_AGENTS_UAMI_HPI")
def expectedDigest = setting("AZURE_CONTAINER_AGENTS_UAMI_SHA256")
def expectedVersion = setting("AZURE_CONTAINER_AGENTS_UAMI_VERSION") ?: "372.v073266fff4a_7-uami.2"
if (!hpiPath || !expectedDigest || !(expectedDigest ==~ /[0-9a-f]{64}/)) {
    throw new IllegalArgumentException("AZURE_CONTAINER_AGENTS_UAMI_HPI and AZURE_CONTAINER_AGENTS_UAMI_SHA256 are required")
}
def hpi = new File(hpiPath).canonicalFile
if (!hpi.isFile() || hpi.name != "azure-container-agents-372.v073266fff4a_7-exact-uami.hpi") {
    throw new IllegalArgumentException("the pinned exact-UAMI azure-container-agents HPI is required")
}
def actualDigest = MessageDigest.getInstance("SHA-256").digest(hpi.bytes).encodeHex().toString()
if (actualDigest != expectedDigest) throw new SecurityException("azure-container-agents exact-UAMI HPI digest mismatch")
def jar = new JarFile(hpi)
def attributes = jar.manifest.mainAttributes
if (attributes.getValue("Short-Name") != "azure-container-agents" || attributes.getValue("Plugin-Version") != expectedVersion) {
    jar.close()
    throw new SecurityException("HPI metadata does not match the pinned exact-UAMI build")
}
jar.close()
def jenkins = Jenkins.get()
def existing = jenkins.pluginManager.getPlugin("azure-container-agents")
if (existing != null && existing.wrapper.archive.toPath() != hpi.toPath()) throw new SecurityException("an unreviewed azure-container-agents plugin is already installed")
if (existing == null) jenkins.pluginManager.dynamicLoad(hpi)
jenkins.save()
println("Installed pinned exact-UAMI azure-container-agents plugin; restart Jenkins before protected scheduling")
