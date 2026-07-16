import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import com.microsoft.azure.util.AzureCredentials
import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import hudson.ExtensionList
import hudson.model.RootAction
import hudson.util.Secret
import jakarta.servlet.http.HttpServletResponse
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.attribute.PosixFilePermissions
import jenkins.model.Jenkins
import org.kohsuke.stapler.RequirePOST
import org.kohsuke.stapler.StaplerRequest2
import org.kohsuke.stapler.StaplerResponse2

class CredentialManagerAction implements RootAction {
    final String managerPrincipal = "jenkins-credential-manager"
    final String allowedCredentialId = "jenkins-azure-cloud"

    String getIconFileName() { null }
    String getDisplayName() { null }
    String getUrlName() { "credential-manager" }

    @RequirePOST
    void doUpdate(StaplerRequest2 request, StaplerResponse2 response) {
        def remote = request.getRemoteAddr()
        if (!(remote in ["127.0.0.1", "0:0:0:0:0:0:0:1", "::1"])) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN)
            return
        }
        if (Jenkins.getAuthentication2().name != managerPrincipal) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN)
            return
        }
        if ((request.contentLengthLong < 1) || (request.contentLengthLong > 16384)) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST)
            return
        }

        def payload = new JsonSlurper().parse(request.reader)
        if (!(payload instanceof Map) || payload.keySet() != ["credentialId", "clientSecret", "version", "expiresAt"] as Set ||
            payload.credentialId != allowedCredentialId || !(payload.clientSecret instanceof String) ||
            payload.clientSecret.length() < 16 || !(payload.version ==~ /[A-Za-z0-9._-]{1,64}/) ||
            !(payload.expiresAt ==~ /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z/)) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST)
            return
        }

        def provider = SystemCredentialsProvider.getInstance()
        def store = provider.store
        def current = provider.credentials.find { it.id == allowedCredentialId }
        if (!(current instanceof AzureCredentials)) {
            response.sendError(HttpServletResponse.SC_CONFLICT)
            return
        }

        def metadataFile = new File(Jenkins.get().rootDir, "credential-health/cloud-metadata.json")
        if (!metadataFile.isFile()) {
            response.sendError(HttpServletResponse.SC_PRECONDITION_FAILED)
            return
        }
        def metadata = new JsonSlurper().parse(metadataFile)
        if (metadata.credentialId != allowedCredentialId) {
            response.sendError(HttpServletResponse.SC_PRECONDITION_FAILED)
            return
        }
        metadata.version = payload.version
        metadata.expiresAt = payload.expiresAt
        metadata.issuedAt = new Date().format("yyyy-MM-dd'T'HH:mm:ss'Z'", TimeZone.getTimeZone("UTC"))
        metadata.capturedAt = metadata.issuedAt
        def temporary = new File(metadataFile.parentFile, ".cloud-metadata.json.tmp")
        temporary.text = JsonOutput.prettyPrint(JsonOutput.toJson(metadata)) + "\n"
        Files.setPosixFilePermissions(temporary.toPath(), PosixFilePermissions.fromString("rw-------"))

        def replacement = new AzureCredentials(
            CredentialsScope.SYSTEM,
            current.id,
            current.description,
            current.subscriptionId,
            current.clientId,
            Secret.fromString(payload.clientSecret)
        )
        if (!store.updateCredentials(Domain.global(), current, replacement)) {
            temporary.delete()
            response.sendError(HttpServletResponse.SC_CONFLICT)
            return
        }
        try {
            Files.move(temporary.toPath(), metadataFile.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
        } catch (Exception ignored) {
            store.updateCredentials(Domain.global(), replacement, current)
            temporary.delete()
            response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR)
            return
        }

        response.contentType = "application/json"
        response.writer.print(JsonOutput.toJson([status: "updated", credentialId: allowedCredentialId, version: payload.version]))
    }
}

def actions = ExtensionList.lookup(RootAction)
actions.removeAll { it instanceof CredentialManagerAction }
actions.add(new CredentialManagerAction())
Jenkins.get().save()

println("Configured localhost-only credential-specific manager action for jenkins-azure-cloud")
