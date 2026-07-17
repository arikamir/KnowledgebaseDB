locals {
  operational_alert_profile  = yamldecode(file("${path.module}/../../config/operational-alert-profile-v1.yaml"))
  pilot_availability_profile = yamldecode(file("${path.module}/../../config/pilot-availability-profile-v1.yaml"))

  operations_action_groups = {
    application-operations      = azurerm_monitor_action_group.application_operations.id
    platform-operations         = azurerm_monitor_action_group.platform_operations.id
    learning-content-operations = azurerm_monitor_action_group.learning_content_operations.id
  }

  operational_query_alerts = {
    readiness                        = { severity = 1, frequency = "PT1M", window = "PT5M", periods = 5, routes = ["application-operations"], query = "KubePodInventory | summarize ready_replicas=countif(PodStatus == 'Running') by bin(TimeGenerated, 1m), ServiceName | where ready_replicas == 0" }
    request-error-rate               = { severity = 1, frequency = "PT5M", window = "PT10M", periods = 2, routes = ["application-operations"], query = "requests | summarize requests=count(), failures=countif(toint(resultCode) >= 500) by bin(timestamp, 5m), cloud_RoleName | extend ratio=100.0*failures/requests | where requests >= 20 and ratio >= 5" }
    latency-p95                      = { severity = 1, frequency = "PT5M", window = "PT10M", periods = 2, routes = ["application-operations"], query = "requests | summarize requests=count(), p95=percentile(duration,95) by bin(timestamp,5m), route_class=tostring(customDimensions.route_class) | extend threshold=case(route_class == 'ui-static',2s, route_class == 'roadmap',30s, route_class == 'guidance',10s,5s) | where requests >= 20 and p95 > threshold" }
    restart-loop                     = { severity = 1, frequency = "PT5M", window = "PT10M", periods = 1, routes = ["application-operations"], query = "KubePodInventory | summarize restarts=max(ContainerRestartCount)-min(ContainerRestartCount) by bin(TimeGenerated,10m), ServiceName | where restarts >= 3" }
    hpa-warning                      = { severity = 2, frequency = "PT5M", window = "PT15M", periods = 3, routes = ["application-operations", "platform-operations"], query = "InsightsMetrics | where Name == 'kube_hpa_status_current_replicas' or Name == 'cpuUsageMillicores' | summarize replicas=max(Val), averageCpuPercent=avg(Val) by bin(TimeGenerated,5m), Namespace | where replicas == 4 and averageCpuPercent >= 70" }
    hpa-page                         = { severity = 1, frequency = "PT5M", window = "PT30M", periods = 6, routes = ["application-operations", "platform-operations"], query = "InsightsMetrics | where Name == 'kube_hpa_status_current_replicas' or Name == 'cpuUsageMillicores' | summarize replicas=max(Val), averageCpuPercent=avg(Val) by bin(TimeGenerated,5m), Namespace | where replicas == 4 and averageCpuPercent >= 70" }
    session-revocation-warning       = { severity = 2, frequency = "PT5M", window = "PT5M", periods = 1, routes = ["application-operations"], query = "customMetrics | where name == 'oldest_unacknowledged_revocation_hours' and value >= 2" }
    session-revocation-page          = { severity = 1, frequency = "PT5M", window = "PT5M", periods = 1, routes = ["application-operations"], query = "customMetrics | where name == 'oldest_unacknowledged_revocation_hours' and value >= 6" }
    session-revocation-critical      = { severity = 0, frequency = "PT5M", window = "PT5M", periods = 1, routes = ["application-operations"], query = "customMetrics | where name == 'oldest_unacknowledged_revocation_hours' and value >= 12" }
    certificate-expiry-30-14-7       = { severity = 2, frequency = "PT1H", window = "PT1H", periods = 1, routes = ["platform-operations"], query = "customMetrics | where name in ('gateway_certificate_expiry_days','private_core_certificate_expiry_days') and value in (30,14,7)" }
    certificate-expiry-critical      = { severity = 0, frequency = "PT5M", window = "PT5M", periods = 1, routes = ["platform-operations"], query = "customMetrics | where name in ('gateway_certificate_expiry_hours','private_core_certificate_expiry_hours') and value < 48" }
    directory-reconciliation-warning = { severity = 2, frequency = "PT30M", window = "PT6H", periods = 1, routes = ["application-operations", "platform-operations"], query = "customMetrics | where name == 'directory_reconciliation_age_hours' and value >= 6" }
    directory-reconciliation-page    = { severity = 1, frequency = "PT30M", window = "PT8H", periods = 1, routes = ["application-operations", "platform-operations"], query = "customMetrics | where name == 'directory_reconciliation_age_hours' and value >= 8" }
    lab-validation-warning           = { severity = 2, frequency = "PT30M", window = "PT30M", periods = 1, routes = ["learning-content-operations"], query = "customMetrics | where name == 'active_lab_validation_age_hours' and value > 30" }
    lab-validation-page              = { severity = 1, frequency = "PT30M", window = "PT30M", periods = 1, routes = ["learning-content-operations", "application-operations"], query = "customMetrics | where (name == 'active_lab_validation_age_hours' and value > 36) or (name == 'lab_consecutive_failures' and value >= 3) or (name == 'lab_unavailable' and value == 1)" }
  }
}

resource "azurerm_application_insights" "app" {
  name                = "appi-${local.stem}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  workspace_id        = azurerm_log_analytics_workspace.app.id
  application_type    = "web"
  tags                = local.tags
}

resource "azurerm_monitor_action_group" "application_operations" {
  name                = "application-operations"
  resource_group_name = azurerm_resource_group.app.name
  short_name          = "appops"
}
resource "azurerm_monitor_action_group" "platform_operations" {
  name                = "platform-operations"
  resource_group_name = azurerm_resource_group.app.name
  short_name          = "platops"
}
resource "azurerm_monitor_action_group" "learning_content_operations" {
  name                = "learning-content-operations"
  resource_group_name = azurerm_resource_group.app.name
  short_name          = "learnops"
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "operational" {
  for_each             = local.operational_query_alerts
  name                 = "${local.stem}-${each.key}"
  resource_group_name  = azurerm_resource_group.app.name
  location             = azurerm_resource_group.app.location
  scopes               = [azurerm_log_analytics_workspace.app.id]
  severity             = each.value.severity
  evaluation_frequency = each.value.frequency
  window_duration      = each.value.window
  criteria {
    query                   = each.value.query
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
    failing_periods {
      minimum_failing_periods_to_trigger_alert = each.value.periods
      number_of_evaluation_periods             = each.value.periods
    }
  }
  action {
    action_groups = [for route in each.value.routes : local.operations_action_groups[route]]
  }
  tags = merge(local.tags, {
    profile             = local.operational_alert_profile.profileId
    required_dimensions = join(",", local.operational_alert_profile.requiredDimensions)
  })
}

# Three PT1M Logic App actions jointly materialize pilot_availability_observation:
# a minute succeeds only when public TLS, runtime configuration, and capabilities pass.
resource "azurerm_logic_app_workflow" "pilot_availability" {
  name                = "${local.stem}-pilot-availability-observation"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  tags                = merge(local.tags, { observation = "pilot_availability_observation", interval = "PT1M" })
}

resource "azurerm_logic_app_trigger_recurrence" "pilot_availability" {
  name         = "eligible-minute"
  logic_app_id = azurerm_logic_app_workflow.pilot_availability.id
  frequency    = "Minute"
  interval     = 1
}

resource "azurerm_logic_app_action_http" "pilot_availability" {
  for_each = {
    public-tls-gateway                     = "/"
    ui-runtime-config                      = "/runtime-config.json"
    bff-v1-capabilities-readiness-contract = "/bff/v1/capabilities"
  }
  name         = each.key
  logic_app_id = azurerm_logic_app_workflow.pilot_availability.id
  method       = "GET"
  uri          = "${trimsuffix(var.pilot_public_url, "/")}${each.value}"
  depends_on   = [azurerm_logic_app_trigger_recurrence.pilot_availability]
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "pilot_availability_missed_observation" {
  name                 = "${local.stem}-pilot-availability-missed-observation"
  resource_group_name  = azurerm_resource_group.app.name
  location             = azurerm_resource_group.app.location
  scopes               = [azurerm_log_analytics_workspace.app.id]
  severity             = 1
  evaluation_frequency = "PT1M"
  window_duration      = "PT5M"
  criteria {
    query                   = "AzureDiagnostics | where TimeGenerated > ago(1m) | where ResourceProvider == 'MICROSOFT.LOGIC' and resource_workflowName_s == '${azurerm_logic_app_workflow.pilot_availability.name}' | summarize passed=dcountif(OperationName == 'Microsoft.Logic/workflows/workflowActionCompleted' and status_s == 'Succeeded', resource_actionName_s) | where passed < 3 // pilot_availability_observation"
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }
  action {
    action_groups = [azurerm_monitor_action_group.application_operations.id]
  }
  tags = merge(local.tags, {
    profile    = local.pilot_availability_profile.profileId
    missed_run = "failed"
    calendar   = "Asia/Jerusalem business days 08:00-18:00"
  })
}
