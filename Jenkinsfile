pipeline {
  agent none

  options {
    skipDefaultCheckout(true)
    disableConcurrentBuilds(abortPrevious: false)
    timestamps()
  }

  parameters {
    booleanParam(name: 'PROTECTED_DELIVERY', defaultValue: false, description: 'Controller-managed protected-ref scheduling marker')
    string(name: 'SOURCE_REVISION', defaultValue: '', description: 'Controller-resolved full source revision used by the pre-node audit')
    choice(name: 'DELIVERY_ACTION', choices: ['normal', 'rebuild-all', 'recovery'], description: 'Protected delivery action')
    string(name: 'BASELINE_REVISION', defaultValue: '', description: 'Full accepted baseline SHA; empty only for a genuine missing baseline')
    string(name: 'RECOVERY_OPERATOR', defaultValue: '', description: 'Delivery Recovery Operator identity')
    string(name: 'PLATFORM_APPROVER', defaultValue: '', description: 'Distinct Platform Operations approver identity')
    string(name: 'RECOVERY_REFERENCE', defaultValue: '', description: 'Quarantined attempt identifier for recovery')
    string(name: 'ACTION_REASON', defaultValue: '', description: 'Required audited reason for manual rebuild or recovery')
  }

  environment {
    CHANGE_PLAN = 'artifacts/change-plan.json'
    RELEASE_DIR = 'artifacts/release'
    DELIVERY_STATE = 'artifacts/delivery-state'
    DELIVERY_EVIDENCE = 'artifacts/evidence'
    PLATFORM_MANIFEST = 'config/platform-bootstrap-nonprod.json'
    DELIVERY_ENVIRONMENT = 'nonprod'
    DELIVERY_NOTIFICATION_STATE_DIR = 'artifacts/delivery-notifications'
  }

  stages {
    stage('Identityless all-ref validation') {
      agent { label 'azure-aci-validator' }
      steps {
        checkout scm
        sh '''
          set -euo pipefail
          mkdir -p artifacts
          args=(--source "$GIT_COMMIT" --output "$CHANGE_PLAN")
          if [[ -n "$BASELINE_REVISION" ]]; then args+=(--baseline "$BASELINE_REVISION"); else args+=(--missing-baseline); fi
          case "$DELIVERY_ACTION" in
            normal) ;;
            rebuild-all|recovery)
              [[ -n "$ACTION_REASON" && -n "$RECOVERY_OPERATOR" && -n "$PLATFORM_APPROVER" && "$RECOVERY_OPERATOR" != "$PLATFORM_APPROVER" ]]
              jq -n --arg action "$DELIVERY_ACTION" --arg reason "$ACTION_REASON" --arg requester "$RECOVERY_OPERATOR" --arg approver "$PLATFORM_APPROVER" --arg revision "$GIT_COMMIT" --arg environment "$DELIVERY_ENVIRONMENT" --arg recoveryReference "$RECOVERY_REFERENCE" '{schemaVersion:1,action:$action,reason:$reason,requester:$requester,approver:$approver,sourceRevision:$revision,environment:$environment,recoveryReference:$recoveryReference}' > artifacts/manual-action-audit.json
              if [[ "$DELIVERY_ACTION" == rebuild-all ]]; then args+=(--rebuild-all); else args+=(--recovery); fi
              args+=(--recovery-operator "$RECOVERY_OPERATOR" --platform-approver "$PLATFORM_APPROVER") ;;
            *) exit 2 ;;
          esac
          scripts/ci/detect-changes.sh "${args[@]}"
          scripts/ci/manage-controller-audit.sh update --run-url "$CONTROLLER_AUDIT_RUN_URL" --netrc-file "$CONTROLLER_AUDIT_NETRC_FILE" --crumb-file "$CONTROLLER_AUDIT_CRUMB_FILE" --stage agent_connected
          scripts/ci/validate-api-contracts.sh
          .venv/bin/python scripts/ci/generate_contracts.py --check
          scripts/ci/validate-service.sh --plan "$CHANGE_PLAN" --lane readinessScenarios -- .venv/bin/pytest -q tests/integration/test_service_outages.py
          scripts/ci/validate-service.sh --plan "$CHANGE_PLAN" --lane performanceProfile -- .venv/bin/pytest -q tests/integration/test_ui_feature_performance.py
          scripts/ci/validate-service.sh --plan "$CHANGE_PLAN" --lane infrastructure -- .venv/bin/pytest -q tests/contract/test_aks_ui_manifests.py tests/contract/test_azure_resource_skills.py
          scripts/ci/validate-non-azure.sh
        '''
        archiveArtifacts artifacts: 'artifacts/change-plan.json,artifacts/manual-action-audit.json', allowEmptyArchive: true, fingerprint: true
        stash name: 'validated-change-plan', includes: 'artifacts/change-plan.json,artifacts/manual-action-audit.json', useDefaultExcludes: false, allowEmpty: false
        junit allowEmptyResults: true, testResults: '**/junit*.xml'
      }
      post {
        unsuccessful {
          sh '[[ "$PROTECTED_DELIVERY" != true ]] || scripts/ci/notify-delivery.sh --build-id "$BUILD_TAG" --event application_pre_mutation_failure --state-dir "$DELIVERY_NOTIFICATION_STATE_DIR" || true'
        }
      }
    }

    stage('Unprotected confinement') {
      when { not { anyOf { branch 'main'; branch pattern: 'release/.+', comparator: 'REGEXP' } } }
      agent none
      steps { echo 'Unprotected ref completed identityless validation; Azure delivery is prohibited.' }
    }

    stage('Protected authorization and live gates') {
      when { anyOf { branch 'main'; branch pattern: 'release/.+', comparator: 'REGEXP' } }
      agent { label 'azure-aci-deployer' }
      steps {
        checkout scm
        unstash 'validated-change-plan'
        sh '''
          set -euo pipefail
          test "${CHANGE_ID:-}" = "" || exit 1
          [[ "$PROTECTED_DELIVERY" == true && "$SOURCE_REVISION" == "$GIT_COMMIT" && "$SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]
          if [[ "$DELIVERY_ACTION" != normal ]]; then
            [[ -n "$RECOVERY_OPERATOR" && -n "$PLATFORM_APPROVER" && "$RECOVERY_OPERATOR" != "$PLATFORM_APPROVER" ]] || exit 1
          fi
          scripts/jenkins/verify-agent.sh --manifest "$PLATFORM_MANIFEST" --actor deployer --resource-id "$AZURE_CLIENT_IDENTITY_RESOURCE_ID"
          scripts/azure/preflight-ui-platform.sh live --repo-root "$WORKSPACE" --manifest "$PLATFORM_MANIFEST"
          scripts/jenkins/verify-aci-identity-binding.sh --manifest "$PLATFORM_MANIFEST" --templates "$ACI_TEMPLATE_REPORT" --runtime-identities "$ACI_RUNTIME_IDENTITY_REPORT" --authorization "$ACI_AUTHORIZATION_REPORT"
          scripts/azure/validate-delivery-identities.sh --mode live --manifest "$PLATFORM_MANIFEST" --report "$DELIVERY_IDENTITY_REPORT"
        '''
      }
      post {
        unsuccessful {
          sh 'scripts/ci/notify-delivery.sh --build-id "$BUILD_TAG" --event platform_pre_mutation_failure --state-dir "$DELIVERY_NOTIFICATION_STATE_DIR" || true'
        }
      }
    }

    stage('Recovery-only bounded reconciliation') {
      when {
        allOf {
          expression { params.DELIVERY_ACTION == 'recovery' }
          anyOf { branch 'main'; branch pattern: 'release/.+', comparator: 'REGEXP' }
        }
      }
      agent { label 'azure-aci-deployer' }
      steps {
        checkout scm
        unstash 'validated-change-plan'
        sh '''
          set -euo pipefail
          [[ -n "$RECOVERY_REFERENCE" ]]
          scripts/ci/rollback.sh recover --journal-dir "$DELIVERY_STATE" --attempt "$RECOVERY_REFERENCE" --namespace "$DELIVERY_ENVIRONMENT" --operator "$RECOVERY_OPERATOR" --operator-role delivery-recovery-operator --approver "$PLATFORM_APPROVER" --approver-role platform-operations
        '''
      }
      post {
        unsuccessful {
          sh 'scripts/ci/notify-delivery.sh --build-id "$BUILD_TAG" --event rollback_failed --state-dir "$DELIVERY_NOTIFICATION_STATE_DIR" || true'
        }
      }
    }

    stage('Build scan publish once') {
      when {
        allOf {
          expression { params.DELIVERY_ACTION != 'recovery' }
          anyOf { branch 'main'; branch pattern: 'release/.+', comparator: 'REGEXP' }
        }
      }
      agent { label 'azure-aci-publisher' }
      steps {
        checkout scm
        unstash 'validated-change-plan'
        sh '''
          set -euo pipefail
          scripts/jenkins/verify-agent.sh --manifest "$PLATFORM_MANIFEST" --actor publisher --resource-id "$AZURE_CLIENT_IDENTITY_RESOURCE_ID"
          scripts/ci/build-publish.sh publish --plan "$CHANGE_PLAN" --build-id "$BUILD_TAG" --revision "$GIT_COMMIT" --registry "$ACR_LOGIN_SERVER" --output-dir "$RELEASE_DIR" --state-dir "$DELIVERY_STATE/unpromoted"
        '''
        stash name: 'published-release', includes: 'artifacts/release/**,artifacts/delivery-state/unpromoted/**', useDefaultExcludes: false
        archiveArtifacts artifacts: 'artifacts/release/**', fingerprint: true
      }
      post {
        unsuccessful {
          sh 'scripts/ci/notify-delivery.sh --build-id "$BUILD_TAG" --event application_pre_mutation_failure --state-dir "$DELIVERY_NOTIFICATION_STATE_DIR" || true'
        }
      }
    }

    stage('Evidence migration promotion verification') {
      when {
        allOf {
          expression { params.DELIVERY_ACTION != 'recovery' }
          anyOf { branch 'main'; branch pattern: 'release/.+', comparator: 'REGEXP' }
        }
      }
      agent { label 'azure-aci-deployer' }
      steps {
        checkout scm
        unstash 'validated-change-plan'
        unstash 'published-release'
        script {
          lock(resource: "delivery-${env.DELIVERY_ENVIRONMENT}", inversePrecedence: true) {
            sh '''
              set -euo pipefail
              scripts/ci/environment-lock.sh acquire --state-dir "$DELIVERY_STATE/locks" --environment "$DELIVERY_ENVIRONMENT" --attempt "$BUILD_TAG" --revision "$GIT_COMMIT" --expected-revision "$GIT_COMMIT"
              trap 'scripts/ci/environment-lock.sh release --state-dir "$DELIVERY_STATE/locks" --environment "$DELIVERY_ENVIRONMENT" --attempt "$BUILD_TAG"' EXIT
              delivery_failure() {
                rc=$?
                event=evidence_failure
                journal="$DELIVERY_STATE/$BUILD_TAG.jsonl"
                if [[ -f "$journal" ]]; then
                  event=post_mutation_failure
                  result="$(tail -n 1 "$journal" | jq -r '.result // ""')"
                  if [[ "$result" == rollback_failed ]]; then
                    event=rollback_failed
                  elif [[ "$result" != rolled_back && "$result" != recovered ]]; then
                    scripts/ci/manage-controller-audit.sh update --run-url "$CONTROLLER_AUDIT_RUN_URL" --netrc-file "$CONTROLLER_AUDIT_NETRC_FILE" --crumb-file "$CONTROLLER_AUDIT_CRUMB_FILE" --stage rollback --environment-mutated true || true
                    scripts/ci/rollback.sh rollback --journal-dir "$DELIVERY_STATE" --attempt "$BUILD_TAG" --namespace "$DELIVERY_ENVIRONMENT" || event=rollback_failed
                  fi
                fi
                scripts/ci/notify-delivery.sh --build-id "$BUILD_TAG" --event "$event" --state-dir "$DELIVERY_NOTIFICATION_STATE_DIR" || true
                exit "$rc"
              }
              trap delivery_failure ERR TERM INT
              scripts/ci/evidence-gate.sh publish --manifest "$DELIVERY_EVIDENCE/pre-promotion/gate-manifest.json" --account "$EVIDENCE_STORAGE_ACCOUNT" --container delivery-evidence --gate-dir "$DELIVERY_EVIDENCE/pre-promotion"
              scripts/ci/evidence-gate.sh check --gate-dir "$DELIVERY_EVIDENCE/pre-promotion" --stage pre-promotion
              if jq -e '.services.core==true' "$CHANGE_PLAN" >/dev/null; then
                scripts/ci/evidence-gate.sh check --gate-dir "$DELIVERY_EVIDENCE/pre-migration" --stage pre-migration
                scripts/ci/migrate-core.sh
                scripts/ci/evidence-gate.sh check --gate-dir "$DELIVERY_EVIDENCE/post-migration" --stage post-migration
              fi
              scripts/ci/evidence-gate.sh check --gate-dir "$DELIVERY_EVIDENCE/pre-mutation" --stage pre-mutation
              scripts/ci/promote.sh --manifest "$RELEASE_DIR/release-manifest.json" --journal-dir "$DELIVERY_STATE" --attempt "$BUILD_TAG" --environment "$DELIVERY_ENVIRONMENT" --snapshot-out "$DELIVERY_STATE/$BUILD_TAG.snapshot.json"
              scripts/ci/evidence-gate.sh check --gate-dir "$DELIVERY_EVIDENCE/post-mutation" --stage post-mutation
              scripts/ci/evidence-gate.sh check --gate-dir "$DELIVERY_EVIDENCE/verification" --stage verification
              scripts/ci/manage-controller-audit.sh update --run-url "$CONTROLLER_AUDIT_RUN_URL" --netrc-file "$CONTROLLER_AUDIT_NETRC_FILE" --crumb-file "$CONTROLLER_AUDIT_CRUMB_FILE" --stage evidence_active --environment-mutated true
              trap - ERR TERM INT
            '''
          }
        }
      }
    }
  }

  post {
    success {
      script {
        if (env.BRANCH_NAME == 'main' || env.BRANCH_NAME ==~ /release\/.+/) {
          node('azure-aci-deployer') {
            checkout scm
            sh 'scripts/ci/notify-delivery.sh --build-id "$BUILD_TAG" --event protected_delivery_succeeded --state-dir "$DELIVERY_NOTIFICATION_STATE_DIR" || true'
          }
        }
      }
    }
    always {
      script {
        def auditLabel = (env.BRANCH_NAME == 'main' || env.BRANCH_NAME ==~ /release\/.+/) ? 'azure-aci-deployer' : 'azure-aci-validator'
        node(auditLabel) {
          checkout scm
          sh '''
            mkdir -p "$DELIVERY_EVIDENCE"
            scripts/ci/manage-controller-audit.sh export --run-url "$CONTROLLER_AUDIT_RUN_URL" --netrc-file "$CONTROLLER_AUDIT_NETRC_FILE" --crumb-file "$CONTROLLER_AUDIT_CRUMB_FILE" --output "$DELIVERY_EVIDENCE/controller-audit.json" || true
          '''
          archiveArtifacts allowEmptyArchive: true, artifacts: 'artifacts/**', fingerprint: true
          cleanWs(deleteDirs: true, disableDeferredWipeout: true)
        }
      }
    }
  }
}
