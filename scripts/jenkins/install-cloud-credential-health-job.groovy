import hudson.model.FreeStyleProject
import hudson.tasks.Shell
import hudson.triggers.TimerTrigger
import jenkins.model.Jenkins

def jenkins = Jenkins.get()
def jobName = "jenkins-cloud-credential-health"
def scriptPath = System.getenv("CREDENTIAL_HEALTH_SCRIPT")
def policyPath = System.getenv("CREDENTIAL_HEALTH_POLICY")
if (!scriptPath || !new File(scriptPath).isFile()) {
    throw new IllegalArgumentException("CREDENTIAL_HEALTH_SCRIPT must name the installed check-cloud-credential-health.sh")
}
if (!policyPath || !new File(policyPath).isFile()) {
    throw new IllegalArgumentException("CREDENTIAL_HEALTH_POLICY must name the installed policy")
}

// jenkins.rootDir is the canonical JENKINS_HOME; no workspace or agent copy is authoritative.
def healthRoot = new File(jenkins.rootDir, "credential-health")
healthRoot.mkdirs()
def report = new File(healthRoot, "cloud-metadata.json")
def assignments = new File(healthRoot, "role-assignments.json")
def state = new File(healthRoot, "state")
def evidence = new File(healthRoot, "evidence")

def job = jenkins.getItemByFullName(jobName, FreeStyleProject)
if (job == null) {
    job = jenkins.createProject(FreeStyleProject, jobName)
}
job.setAssignedLabel(jenkins.selfLabel)
job.setConcurrentBuild(false)
job.setDescription("Controller-local non-secret daily validation for cloud azure credential expiry and scope")
job.buildersList.clear()
job.buildersList.add(new Shell(
    "umask 077\nexec '${scriptPath}' --metadata '${report}' --assignments '${assignments}' " +
    "--policy '${policyPath}' --state-dir '${state}' --evidence-dir '${evidence}'"
))
job.triggers.clear()
job.addTrigger(new TimerTrigger("H H * * *"))
job.save()

println("Installed controller-local jenkins-cloud-credential-health schedule")
