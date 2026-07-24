package io.knowledgebasedb.jenkins.audit;

import hudson.Extension;
import hudson.model.Cause;
import hudson.model.ParametersAction;
import hudson.model.Result;
import hudson.model.Run;
import hudson.model.TaskListener;
import hudson.model.listeners.RunListener;
import java.io.IOException;

@Extension
public final class ControllerAuditRunListener extends RunListener<Run<?, ?>> {
    @Override public void onStarted(Run<?, ?> run, TaskListener listener) {
        if (run.getCauses().isEmpty()) return; // an unaccepted trigger never reaches a Run
        String revision = "unknown";
        ParametersAction parameters = run.getAction(ParametersAction.class);
        if (parameters != null && parameters.getParameter("SOURCE_REVISION") != null) revision = String.valueOf(parameters.getParameter("SOURCE_REVISION").getValue());
        ControllerAuditAction action = new ControllerAuditAction(run, revision);
        run.addAction(action);
        try { action.start(); } catch (IOException exception) { run.setResult(Result.FAILURE); throw new IllegalStateException("controller audit acceptance fsync failed", exception); }
    }
    @Override public void onCompleted(Run<?, ?> run, TaskListener listener) {
        ControllerAuditAction action = run.getAction(ControllerAuditAction.class); if (action == null) return;
        String terminal = run.getResult() == Result.SUCCESS ? "succeeded" : run.getResult() == Result.ABORTED ? "aborted" : "failed";
        try { action.finalizeOnce(terminal, terminal.equals("succeeded") ? "none" : "jenkins"); }
        catch (IOException exception) { throw new IllegalStateException("controller audit terminal fsync failed", exception); }
    }
    @Override public void onFinalized(Run<?, ?> run) {
        ControllerAuditAction action = run.getAction(ControllerAuditAction.class); if (action == null || action.isTerminal()) return;
        String terminal = run.getResult() == Result.SUCCESS ? "succeeded" : run.getResult() == Result.ABORTED ? "aborted" : "failed";
        try { action.finalizeOnce(terminal, terminal.equals("succeeded") ? "none" : "jenkins"); }
        catch (IOException exception) { throw new IllegalStateException("controller audit finalization retry failed", exception); }
    }
}
