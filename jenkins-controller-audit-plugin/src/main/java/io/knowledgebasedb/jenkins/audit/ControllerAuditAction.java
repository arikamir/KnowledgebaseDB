package io.knowledgebasedb.jenkins.audit;

import hudson.model.Action;
import hudson.model.Item;
import hudson.model.Run;
import hudson.util.HttpResponses;
import java.io.IOException;
import java.time.Instant;
import java.util.List;
import net.sf.json.JSONObject;
import jenkins.model.RunAction2;
import org.kohsuke.stapler.HttpResponse;
import org.kohsuke.stapler.QueryParameter;
import org.kohsuke.stapler.interceptor.RequirePOST;

public final class ControllerAuditAction implements Action, RunAction2 {
    private static final long serialVersionUID = 1L;
    private static final List<String> STAGES = List.of("started", "agent_requested", "agent_connected", "evidence_active", "pre_promotion", "pre_migration", "post_migration", "pre_mutation", "post_mutation", "verification", "rollback");
    private final String buildId, sourceRevision, startedAt;
    private String result = "pending", failedStage;
    private String completedAt;
    private int stageIndex = 0;
    private boolean terminalFinalized, environmentMutated;
    private transient Run<?, ?> run;

    ControllerAuditAction(Run<?, ?> run, String sourceRevision) {
        this.run = run; this.buildId = run.getExternalizableId(); this.sourceRevision = sourceRevision; this.startedAt = Instant.now().toString();
    }
    ControllerAuditAction(Run<?, ?> run, String sourceRevision, String startedAt, boolean environmentMutated) {
        this.run = run; this.buildId = run.getExternalizableId(); this.sourceRevision = sourceRevision; this.startedAt = startedAt; this.environmentMutated = environmentMutated;
    }
    @Override public String getIconFileName() { return null; }
    @Override public String getDisplayName() { return null; }
    @Override public String getUrlName() { return "controller-audit"; }
    @Override public void onAttached(Run<?, ?> run) { this.run = run; }
    @Override public void onLoad(Run<?, ?> run) { this.run = run; }

    synchronized void start() throws IOException { persist("started", "pending", null); }
    synchronized void restoredFromReplica() throws IOException { persist("restored_from_replica", "pending", null); }
    synchronized void transition(String stage, boolean mutated) throws IOException {
        if (terminalFinalized) throw new IOException("controller audit is terminal");
        int next = STAGES.indexOf(stage);
        if (next < stageIndex || next < 0) throw new IOException("non-monotonic controller audit transition");
        stageIndex = next; environmentMutated |= mutated; persist(stage, "pending", null);
    }
    synchronized boolean finalizeOnce(String terminal, String failed) throws IOException {
        if (terminalFinalized) return false;
        if (!List.of("succeeded", "failed", "aborted", "aborted_recovered").contains(terminal)) throw new IOException("invalid terminal result");
        String priorResult = result, priorFailed = failedStage, priorCompleted = completedAt;
        terminalFinalized = true; result = terminal; failedStage = failed == null ? "none" : failed; completedAt = Instant.now().toString();
        try { persist("terminal", terminal, failedStage); return true; }
        catch (IOException exception) { terminalFinalized = false; result = priorResult; failedStage = priorFailed; completedAt = priorCompleted; run.save(); throw exception; }
    }
    private void persist(String eventName, String eventResult, String failed) throws IOException {
        JSONObject event = new JSONObject(); event.put("schemaVersion", 1); event.put("buildId", buildId); event.put("sourceRevision", sourceRevision);
        event.put("event", eventName); event.put("at", Instant.now().toString()); event.put("result", eventResult); event.put("failedStage", failed);
        event.put("environmentMutated", environmentMutated); event.put("controllerLocalAuthoritative", false);
        ControllerAuditStore.persistBoth(run, event);
    }
    @RequirePOST public HttpResponse doUpdate(@QueryParameter String stage, @QueryParameter boolean environmentMutated) {
        run.getParent().checkPermission(Item.BUILD);
        try { transition(stage, environmentMutated); return HttpResponses.okJSON(export()); }
        catch (IOException exception) { return HttpResponses.errorJSON(exception.getMessage()); }
    }
    @RequirePOST public HttpResponse doExport() {
        run.getParent().checkPermission(Item.READ);
        if (stageIndex < STAGES.indexOf("evidence_active")) return HttpResponses.errorWithoutStack(409, "evidence is not active");
        return HttpResponses.okJSON(export());
    }
    JSONObject export() {
        JSONObject value = new JSONObject(); value.put("schemaVersion", 1); value.put("buildId", buildId); value.put("sourceRevision", sourceRevision);
        value.put("startedAt", startedAt); value.put("completedAt", completedAt); value.put("result", result); value.put("failedStage", failedStage);
        value.put("environmentMutated", environmentMutated); value.put("controllerLocalAuthoritative", false); return value;
    }
    boolean isTerminal() { return terminalFinalized; }
    boolean hasMutation() { return environmentMutated; }
}
