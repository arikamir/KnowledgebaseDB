import jenkins.model.Jenkins
import java.security.MessageDigest
import java.util.jar.JarFile

def hpiPath = System.getenv("CONTROLLER_AUDIT_HPI")
def expectedDigest = System.getenv("CONTROLLER_AUDIT_SHA256")
def protectedRevision = System.getenv("CONTROLLER_AUDIT_PROTECTED_REVISION")
if (!hpiPath || !expectedDigest || !protectedRevision || !(expectedDigest ==~ /[0-9a-f]{64}/) || !(protectedRevision ==~ /[0-9a-f]{40}/)) {
    throw new IllegalArgumentException("pinned HPI, SHA-256, and protected revision are required")
}
def hpi = new File(hpiPath).canonicalFile
if (!hpi.isFile() || hpi.name != "controller-audit.hpi") throw new IllegalArgumentException("installed controller-audit.hpi required")
def actualDigest = MessageDigest.getInstance("SHA-256").digest(hpi.bytes).encodeHex().toString()
if (actualDigest != expectedDigest) throw new SecurityException("controller-audit HPI digest mismatch")
def jar = new JarFile(hpi)
def manifest = jar.manifest.mainAttributes
if (manifest.getValue("Short-Name") != "controller-audit" || manifest.getValue("Implementation-Build") != protectedRevision) {
    throw new SecurityException("controller-audit HPI was not built from the pinned protected revision")
}
jar.close()
def jenkins = Jenkins.get()
def existing = jenkins.pluginManager.getPlugin("controller-audit")
if (existing != null && existing.wrapper.archive.toPath() != hpi.toPath()) throw new SecurityException("unreviewed controller-audit plugin already installed")
if (existing == null) jenkins.pluginManager.dynamicLoad(hpi)
jenkins.save()
println("Installed pinned protected-revision controller-audit plugin; restart Jenkins before protected scheduling")
