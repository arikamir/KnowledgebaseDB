package io.knowledgebasedb.jenkins.audit;

import hudson.Extension;
import hudson.model.AsyncPeriodicWork;
import hudson.model.Run;
import hudson.model.TaskListener;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;
import net.sf.json.JSONObject;

@Extension
public final class ControllerAuditMaintenance extends AsyncPeriodicWork {
    public ControllerAuditMaintenance() { super("controller-audit-reconcile-retain"); }
    @Override public long getRecurrencePeriod() { return 5L * 60 * 1000; }
    @Override protected void execute(TaskListener listener) throws IOException, InterruptedException {
        if (!ControllerAuditStore.writable()) return;
        Path requests = ControllerAuditStore.directory().resolve("reconciliation");
        if (Files.isDirectory(requests)) try (var paths = Files.list(requests)) {
            for (Path request : paths.filter(path -> path.getFileName().toString().endsWith(".json")).toList()) reconcile(request);
        }
        ControllerAuditStore.retentionCleanup();
    }
    private void reconcile(Path request) throws IOException {
        JSONObject input = JSONObject.fromObject(Files.readString(request));
        if (!input.keySet().equals(java.util.Set.of("buildId", "queueAccepted", "webhookAccepted", "azureEvidenceFound", "environmentMutated", "recoveryVerified"))) return;
        if (!input.getBoolean("queueAccepted") || !input.getBoolean("webhookAccepted")) return;
        Run<?, ?> run = Run.fromExternalizableId(input.getString("buildId"));
        if (run == null) return;
        ControllerAuditAction action = run.getAction(ControllerAuditAction.class);
        if (action == null) {
            Path replica = ControllerAuditStore.directory().resolve(ControllerAuditStore.fileKey(input.getString("buildId")) + ".jsonl");
            if (!Files.isRegularFile(replica)) return;
            List<String> lines = Files.readAllLines(replica); if (lines.isEmpty()) return;
            JSONObject first = JSONObject.fromObject(lines.get(0)); JSONObject last = JSONObject.fromObject(lines.get(lines.size() - 1));
            action = new ControllerAuditAction(run, first.optString("sourceRevision", "unknown"), first.getString("at"), last.optBoolean("environmentMutated", false));
            run.addAction(action); action.restoredFromReplica();
        }
        if (action != null && !action.isTerminal()) action.finalizeOnce("aborted_recovered", "controller-recovery");
        if (input.getBoolean("environmentMutated") && !input.getBoolean("recoveryVerified")) {
            ControllerAuditStore.blockRecovery(input.getString("buildId"));
        }
        if (input.getBoolean("environmentMutated") && input.getBoolean("recoveryVerified")) ControllerAuditStore.releaseRecovery(input.getString("buildId"));
        Files.move(request, request.resolveSibling(request.getFileName() + ".reconciled"));
    }
}
