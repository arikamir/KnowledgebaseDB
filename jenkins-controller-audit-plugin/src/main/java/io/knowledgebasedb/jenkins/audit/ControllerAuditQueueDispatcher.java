package io.knowledgebasedb.jenkins.audit;

import hudson.Extension;
import hudson.model.ParameterValue;
import hudson.model.ParametersAction;
import hudson.model.Queue;
import hudson.model.queue.CauseOfBlockage;
import hudson.model.queue.QueueTaskDispatcher;

@Extension
public final class ControllerAuditQueueDispatcher extends QueueTaskDispatcher {
    private static CauseOfBlockage blocked(String message) { return new CauseOfBlockage() { @Override public String getShortDescription() { return message; } }; }
    @Override public CauseOfBlockage canRun(Queue.Item item) {
        ParametersAction parameters = item.getAction(ParametersAction.class);
        ParameterValue protectedValue = parameters == null ? null : parameters.getParameter("PROTECTED_DELIVERY");
        boolean protectedDelivery = protectedValue != null && Boolean.parseBoolean(String.valueOf(protectedValue.getValue()));
        if (protectedDelivery && !ControllerAuditStore.healthy()) return blocked("protected scheduling denied: replicated controller-audit store unhealthy or recovery-blocked");
        ParameterValue revision = parameters == null ? null : parameters.getParameter("SOURCE_REVISION");
        if (protectedDelivery && (revision == null || !String.valueOf(revision.getValue()).matches("[0-9a-f]{40}"))) return blocked("protected scheduling denied: exact source revision missing");
        return null;
    }
}
