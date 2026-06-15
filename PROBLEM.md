
softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ # 1. Kill any in-flight auto-sync from the controller
argocd app terminate-op monitoring-stack-staging
sleep 5

# 2. Force ArgoCD to pull the new GitHub commit immediately (don't wait the 3-min poll)
argocd app get monitoring-stack-staging --refresh

# 3. Sync
argocd app sync monitoring-stack-staging --timeout 600
argocd app wait monitoring-stack-staging --health --timeout 600
Application 'monitoring-stack-staging' operation terminating
Name:               argocd/monitoring-stack-staging
Project:            monitoring
Server:             https://kubernetes.default.svc
Namespace:          monitoring
URL:                https://127.0.0.1:8080/applications/monitoring-stack-staging
Sources:
- Repo:             https://prometheus-community.github.io/helm-charts
  Target:           65.5.0
  Helm Values:      $values/helm/monitoring-stack/values-staging.yaml
- Repo:             https://github.com/FlameGreat-1/eTradie.git
  Target:           main
  Ref:              values
SyncWindow:         Sync Allowed
Sync Policy:        Automated (Prune)
Sync Status:        OutOfSync from 65.5.0
Health Status:      Missing

GROUP                         KIND                            NAMESPACE   NAME                                                     STATUS     HEALTH   HOOK     MESSAGE
                              Namespace                                   monitoring                                               Running    Synced            namespace/monitoring serverside-applied
                              ServiceAccount                  monitoring  kube-prometheus-stack-admission                          Succeeded           PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     ClusterRole                     monitoring  kube-prometheus-stack-admission                          Succeeded           PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     ClusterRoleBinding              monitoring  kube-prometheus-stack-admission                          Succeeded           PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     Role                            monitoring  kube-prometheus-stack-admission                          Succeeded           PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     RoleBinding                     monitoring  kube-prometheus-stack-admission                          Succeeded           PreSync  kube-prometheus-stack-admission created
batch                         Job                             monitoring  kube-prometheus-stack-admission-create                   Running             PreSync  job.batch/kube-prometheus-stack-admission-create serverside-applied
                              ConfigMap                       monitoring  kube-prometheus-stack-alertmanager-overview              OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-apiserver                          OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-cluster-total                      OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-grafana-config-dashboards          OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-grafana-datasource                 OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-grafana-overview                   OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-cluster              OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-multicluster         OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-namespace            OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-node                 OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-pod                  OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-workload             OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-k8s-resources-workloads-namespace  OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-kubelet                            OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-namespace-by-pod                   OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-namespace-by-workload              OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-node-cluster-rsrc-use              OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-node-rsrc-use                      OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-nodes                              OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-nodes-aix                          OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-nodes-darwin                       OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-persistentvolumesusage             OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-pod-total                          OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-prometheus                         OutOfSync  Missing
                              ConfigMap                       monitoring  kube-prometheus-stack-workload-total                     OutOfSync  Missing
                              Secret                          monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
                              Service                         monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
                              Service                         monitoring  kube-prometheus-stack-kube-state-metrics                 OutOfSync  Missing
                              Service                         monitoring  kube-prometheus-stack-operator                           OutOfSync  Missing
                              Service                         monitoring  kube-prometheus-stack-prometheus                         OutOfSync  Missing
                              Service                         monitoring  kube-prometheus-stack-prometheus-node-exporter           OutOfSync  Missing
                              ServiceAccount                  monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
                              ServiceAccount                  monitoring  kube-prometheus-stack-kube-state-metrics                 OutOfSync  Missing
                              ServiceAccount                  monitoring  kube-prometheus-stack-operator                           OutOfSync  Missing
                              ServiceAccount                  monitoring  kube-prometheus-stack-prometheus                         OutOfSync  Missing
                              ServiceAccount                  monitoring  kube-prometheus-stack-prometheus-node-exporter           OutOfSync  Missing
admissionregistration.k8s.io  MutatingWebhookConfiguration                kube-prometheus-stack-admission                          OutOfSync  Missing
admissionregistration.k8s.io  ValidatingWebhookConfiguration              kube-prometheus-stack-admission                          OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    alertmanagerconfigs.monitoring.coreos.com                OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    alertmanagers.monitoring.coreos.com                      OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    podmonitors.monitoring.coreos.com                        OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    probes.monitoring.coreos.com                             OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    prometheusagents.monitoring.coreos.com                   OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    prometheuses.monitoring.coreos.com                       OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    prometheusrules.monitoring.coreos.com                    OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    scrapeconfigs.monitoring.coreos.com                      OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    servicemonitors.monitoring.coreos.com                    OutOfSync  Missing
apiextensions.k8s.io          CustomResourceDefinition                    thanosrulers.monitoring.coreos.com                       OutOfSync  Missing
apps                          DaemonSet                       monitoring  kube-prometheus-stack-prometheus-node-exporter           OutOfSync  Missing
apps                          Deployment                      monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
apps                          Deployment                      monitoring  kube-prometheus-stack-kube-state-metrics                 OutOfSync  Missing
apps                          Deployment                      monitoring  kube-prometheus-stack-operator                           OutOfSync  Missing
monitoring.coreos.com         Prometheus                      monitoring  kube-prometheus-stack-prometheus                         Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  coredns                                                  Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-apiserver                          Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-grafana                            Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-kube-state-metrics                 Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-kubelet                            Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-operator                           Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-prometheus                         Unknown    Missing
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-prometheus-node-exporter           Unknown    Missing
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-admission
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-grafana-clusterrole                OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-kube-state-metrics                 OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-operator                           OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-prometheus                         OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-admission
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-grafana-clusterrolebinding         OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-kube-state-metrics                 OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-operator                           OutOfSync  Missing
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-prometheus                         OutOfSync  Missing
rbac.authorization.k8s.io     Role                            monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
rbac.authorization.k8s.io     RoleBinding                     monitoring  kube-prometheus-stack-grafana                            OutOfSync  Missing
FATA[0004] rpc error: code = FailedPrecondition desc = another operation is already in progress
TIMESTAMP                  GROUP                            KIND                 NAMESPACE                  NAME                                       STATUS    HEALTH        HOOK  MESSAGE
2026-06-15T08:18:24+01:00  monitoring.coreos.com      ServiceMonitor            monitoring               coredns                                       Synced                        servicemonitor.monitoring.coreos.com/coredns serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition              podmonitors.monitoring.coreos.com                          Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io        Role                monitoring  kube-prometheus-stack-admission                          Succeeded              PreSync  kube-prometheus-stack-admission created
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-apiserver                            Synced                        configmap/kube-prometheus-stack-apiserver serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-k8s-resources-workloads-namespace    Synced                        configmap/kube-prometheus-stack-k8s-resources-workloads-namespace serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition  monitoring  scrapeconfigs.monitoring.coreos.com                      Succeeded   Synced              customresourcedefinition.apiextensions.k8s.io/scrapeconfigs.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRoleBinding        monitoring  kube-prometheus-stack-kube-state-metrics                 Succeeded   Synced              clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics reconciled. reconciliation required create
                           missing subjects added:
                                                         {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-kube-state-metrics Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:24+01:00   apps                         Deployment                      monitoring  kube-prometheus-stack-grafana                       Synced   Progressing              deployment.apps/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition                    prometheusrules.monitoring.coreos.com               Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-admission
2026-06-15T08:18:24+01:00                                ServiceAccount                  monitoring  kube-prometheus-stack-admission                   Succeeded                  PreSync  kube-prometheus-stack-admission created
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-prometheus                    Synced                            configmap/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-prometheus-node-exporter      Synced                            servicemonitor.monitoring.coreos.com/kube-prometheus-stack-prometheus-node-exporter serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition                    prometheusagents.monitoring.coreos.com              Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-operator                      Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRole                     monitoring  kube-prometheus-stack-admission                   Succeeded                  PreSync  kube-prometheus-stack-admission created
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-namespace-by-pod              Synced                            configmap/kube-prometheus-stack-namespace-by-pod serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-cluster-total                 Synced                            configmap/kube-prometheus-stack-cluster-total serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io           Role                      monitoring  kube-prometheus-stack-grafana                       Synced                            role.rbac.authorization.k8s.io/kube-prometheus-stack-grafana reconciled. reconciliation required create. role.rbac.authorization.k8s.io/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition                    servicemonitors.monitoring.coreos.com               Synced
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-workload-total                Synced                            configmap/kube-prometheus-stack-workload-total serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition        monitoring  prometheusagents.monitoring.coreos.com            Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/prometheusagents.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition        monitoring  alertmanagerconfigs.monitoring.coreos.com         Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/alertmanagerconfigs.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00                                   Service                      monitoring  kube-prometheus-stack-kube-state-metrics            Synced   Healthy                  service/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:24+01:00                                 Namespace                                            monitoring                               Running    Synced                  namespace/monitoring serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-nodes-darwin                  Synced                            configmap/kube-prometheus-stack-nodes-darwin serverside-applied
2026-06-15T08:18:24+01:00                                ServiceAccount                  monitoring  kube-prometheus-stack-prometheus-node-exporter      Synced                            serviceaccount/kube-prometheus-stack-prometheus-node-exporter serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-kubelet                       Synced                            configmap/kube-prometheus-stack-kubelet serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition        monitoring  servicemonitors.monitoring.coreos.com             Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/servicemonitors.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  admissionregistration.k8s.io  MutatingWebhookConfiguration    monitoring  kube-prometheus-stack-admission                   Succeeded   Synced                  mutatingwebhookconfiguration.admissionregistration.k8s.io/kube-prometheus-stack-admission serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-grafana-clusterrole           Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-kube-state-metrics            Synced
2026-06-15T08:18:24+01:00   apps                          DaemonSet                      monitoring  kube-prometheus-stack-prometheus-node-exporter      Synced   Healthy                  daemonset.apps/kube-prometheus-stack-prometheus-node-exporter serverside-applied
2026-06-15T08:18:24+01:00  admissionregistration.k8s.io  ValidatingWebhookConfiguration              kube-prometheus-stack-admission                     Synced
2026-06-15T08:18:24+01:00  batch                                Job                      monitoring  kube-prometheus-stack-admission-create            Succeeded                  PreSync  job.batch/kube-prometheus-stack-admission-create serverside-applied
2026-06-15T08:18:24+01:00                                    Secret                      monitoring  kube-prometheus-stack-grafana                       Synced                            secret/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-k8s-resources-namespace       Synced                            configmap/kube-prometheus-stack-k8s-resources-namespace serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-pod-total                     Synced                            configmap/kube-prometheus-stack-pod-total serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition        monitoring  thanosrulers.monitoring.coreos.com                Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/thanosrulers.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRoleBinding              monitoring  kube-prometheus-stack-grafana-clusterrolebinding  Succeeded   Synced                  clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrolebinding reconciled. reconciliation required create
                           missing subjects added:
                                                      {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-grafana Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrolebinding serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition              scrapeconfigs.monitoring.coreos.com            Synced
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition              probes.monitoring.coreos.com                   Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRole                           kube-prometheus-stack-prometheus               Synced
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-alertmanager-overview    Synced                        configmap/kube-prometheus-stack-alertmanager-overview serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRole               monitoring  kube-prometheus-stack-operator               Succeeded   Synced              clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-operator reconciled. reconciliation required create
                           missing rules added:
                                                      {Verbs:[*] APIGroups:[monitoring.coreos.com] Resources:[alertmanagers alertmanagers/finalizers alertmanagers/status alertmanagerconfigs prometheuses prometheuses/finalizers prometheuses/status prometheusagents prometheusagents/finalizers prometheusagents/status thanosrulers thanosrulers/finalizers thanosrulers/status scrapeconfigs servicemonitors podmonitors probes prometheusrules] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[*] APIGroups:[apps] Resources:[statefulsets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[*] APIGroups:[] Resources:[configmaps secrets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list delete] APIGroups:[] Resources:[pods] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get create update delete] APIGroups:[] Resources:[services services/finalizers endpoints] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[nodes] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get list watch] APIGroups:[] Resources:[namespaces] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[patch create] APIGroups:[] Resources:[events] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get list watch] APIGroups:[networking.k8s.io] Resources:[ingresses] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get] APIGroups:[storage.k8s.io] Resources:[storageclasses] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get create list watch update delete] APIGroups:[discovery.k8s.io] Resources:[endpointslices] ResourceNames:[] NonResourceURLs:[]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-operator serverside-applied
2026-06-15T08:18:24+01:00                                Service                monitoring  kube-prometheus-stack-prometheus-node-exporter      Synced   Healthy                  service/kube-prometheus-stack-prometheus-node-exporter serverside-applied
2026-06-15T08:18:24+01:00                                Service                monitoring  kube-prometheus-stack-operator                      Synced   Healthy                  service/kube-prometheus-stack-operator serverside-applied
2026-06-15T08:18:24+01:00   apps                      Deployment                monitoring  kube-prometheus-stack-kube-state-metrics            Synced   Progressing              deployment.apps/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition              alertmanagers.monitoring.coreos.com                 Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRoleBinding                    kube-prometheus-stack-admission
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-k8s-resources-multicluster    Synced                            configmap/kube-prometheus-stack-k8s-resources-multicluster serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-k8s-resources-workload        Synced                            configmap/kube-prometheus-stack-k8s-resources-workload serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition  monitoring  prometheusrules.monitoring.coreos.com             Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/prometheusrules.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition  monitoring  podmonitors.monitoring.coreos.com                 Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/podmonitors.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition  monitoring  prometheuses.monitoring.coreos.com                Succeeded   Synced                  customresourcedefinition.apiextensions.k8s.io/prometheuses.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00                                Service                monitoring  kube-prometheus-stack-prometheus                    Synced   Healthy                  service/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com      ServiceMonitor            monitoring  kube-prometheus-stack-grafana                       Synced                            servicemonitor.monitoring.coreos.com/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com      ServiceMonitor            monitoring  kube-prometheus-stack-prometheus                    Synced                            servicemonitor.monitoring.coreos.com/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-k8s-resources-pod             Synced                            configmap/kube-prometheus-stack-k8s-resources-pod serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-grafana                       Synced                            configmap/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-nodes                         Synced                            configmap/kube-prometheus-stack-nodes serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-k8s-resources-node            Synced                            configmap/kube-prometheus-stack-k8s-resources-node serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-persistentvolumesusage        Synced                            configmap/kube-prometheus-stack-persistentvolumesusage serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRole               monitoring  kube-prometheus-stack-grafana-clusterrole         Succeeded   Synced                  clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrole reconciled. reconciliation required create
                           missing rules added:
                                                         {Verbs:[get watch list] APIGroups:[] Resources:[configmaps secrets] ResourceNames:[] NonResourceURLs:[]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrole serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition                    alertmanagerconfigs.monitoring.coreos.com          Synced
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition                    thanosrulers.monitoring.coreos.com                 Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-kube-state-metrics           Synced
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-grafana-config-dashboards    Synced                        configmap/kube-prometheus-stack-grafana-config-dashboards serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-nodes-aix                    Synced                        configmap/kube-prometheus-stack-nodes-aix serverside-applied
2026-06-15T08:18:24+01:00                                   Service                      monitoring  kube-prometheus-stack-grafana                      Synced   Healthy              service/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00  admissionregistration.k8s.io  ValidatingWebhookConfiguration  monitoring  kube-prometheus-stack-admission                  Succeeded   Synced              validatingwebhookconfiguration.admissionregistration.k8s.io/kube-prometheus-stack-admission serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-apiserver                    Synced                        servicemonitor.monitoring.coreos.com/kube-prometheus-stack-apiserver serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRoleBinding              monitoring  kube-prometheus-stack-admission                  Succeeded              PreSync  kube-prometheus-stack-admission created
2026-06-15T08:18:24+01:00                                ServiceAccount                  monitoring  kube-prometheus-stack-kube-state-metrics           Synced                        serviceaccount/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-grafana-overview             Synced                        configmap/kube-prometheus-stack-grafana-overview serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-namespace-by-workload        Synced                        configmap/kube-prometheus-stack-namespace-by-workload serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition        monitoring  probes.monitoring.coreos.com                     Succeeded   Synced              customresourcedefinition.apiextensions.k8s.io/probes.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00   apps                         Deployment                      monitoring  kube-prometheus-stack-operator                     Synced   Healthy              deployment.apps/kube-prometheus-stack-operator serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-prometheus                   Synced
2026-06-15T08:18:24+01:00  monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-kube-state-metrics           Synced                        servicemonitor.monitoring.coreos.com/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-kubelet                      Synced                        servicemonitor.monitoring.coreos.com/kube-prometheus-stack-kubelet serverside-applied
2026-06-15T08:18:24+01:00                                ServiceAccount                  monitoring  kube-prometheus-stack-prometheus                   Synced                        serviceaccount/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-k8s-resources-cluster        Synced                        configmap/kube-prometheus-stack-k8s-resources-cluster serverside-applied
2026-06-15T08:18:24+01:00                                 ConfigMap                      monitoring  kube-prometheus-stack-node-rsrc-use                Synced                        configmap/kube-prometheus-stack-node-rsrc-use serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     ClusterRole                     monitoring  kube-prometheus-stack-kube-state-metrics         Succeeded   Synced              clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics reconciled. reconciliation required create
                           missing rules added:
                                                      {Verbs:[list watch] APIGroups:[certificates.k8s.io] Resources:[certificatesigningrequests] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[configmaps] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[batch] Resources:[cronjobs] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[extensions apps] Resources:[daemonsets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[extensions apps] Resources:[deployments] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[endpoints] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[autoscaling] Resources:[horizontalpodautoscalers] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[extensions networking.k8s.io] Resources:[ingresses] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[batch] Resources:[jobs] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[coordination.k8s.io] Resources:[leases] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[limitranges] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[admissionregistration.k8s.io] Resources:[mutatingwebhookconfigurations] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[namespaces] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[networking.k8s.io] Resources:[networkpolicies] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[nodes] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[persistentvolumeclaims] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[persistentvolumes] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[policy] Resources:[poddisruptionbudgets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[pods] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[extensions apps] Resources:[replicasets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[replicationcontrollers] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[resourcequotas] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[secrets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[] Resources:[services] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[apps] Resources:[statefulsets] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[storage.k8s.io] Resources:[storageclasses] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[admissionregistration.k8s.io] Resources:[validatingwebhookconfigurations] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[list watch] APIGroups:[storage.k8s.io] Resources:[volumeattachments] ResourceNames:[] NonResourceURLs:[]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRoleBinding  monitoring  kube-prometheus-stack-prometheus  Succeeded   Synced              clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus reconciled. reconciliation required create
                           missing subjects added:
                                                      {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-prometheus Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRoleBinding  monitoring  kube-prometheus-stack-operator  Succeeded   Synced              clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-operator reconciled. reconciliation required create
                           missing subjects added:
                                                         {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-operator Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-operator serverside-applied
2026-06-15T08:18:24+01:00  admissionregistration.k8s.io  MutatingWebhookConfiguration              kube-prometheus-stack-admission        Synced
2026-06-15T08:18:24+01:00  apiextensions.k8s.io          CustomResourceDefinition      monitoring  alertmanagers.monitoring.coreos.com  Succeeded   Synced              customresourcedefinition.apiextensions.k8s.io/alertmanagers.monitoring.coreos.com serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io     RoleBinding                   monitoring  kube-prometheus-stack-grafana          Synced                        rolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana reconciled. reconciliation required create
                           missing subjects added:
                                                      {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-grafana Namespace:monitoring}. rolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com      ServiceMonitor      monitoring  kube-prometheus-stack-operator                      Synced                         servicemonitor.monitoring.coreos.com/kube-prometheus-stack-operator serverside-applied
2026-06-15T08:18:24+01:00  monitoring.coreos.com      Prometheus          monitoring  kube-prometheus-stack-prometheus                    Synced   Degraded              prometheus.monitoring.coreos.com/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRoleBinding              kube-prometheus-stack-grafana-clusterrolebinding    Synced
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  RoleBinding         monitoring  kube-prometheus-stack-admission                   Succeeded               PreSync  kube-prometheus-stack-admission created
2026-06-15T08:18:24+01:00                             ServiceAccount      monitoring  kube-prometheus-stack-operator                      Synced                         serviceaccount/kube-prometheus-stack-operator serverside-applied
2026-06-15T08:18:24+01:00                             ServiceAccount      monitoring  kube-prometheus-stack-grafana                       Synced                         serviceaccount/kube-prometheus-stack-grafana serverside-applied
2026-06-15T08:18:24+01:00                              ConfigMap          monitoring  kube-prometheus-stack-grafana-datasource            Synced                         configmap/kube-prometheus-stack-grafana-datasource serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRole         monitoring  kube-prometheus-stack-prometheus                  Succeeded   Synced               clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus reconciled. reconciliation required create
                           missing rules added:
                                                      {Verbs:[get list watch] APIGroups:[] Resources:[nodes nodes/metrics services endpoints pods] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get list watch] APIGroups:[discovery.k8s.io] Resources:[endpointslices] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get list watch] APIGroups:[networking.k8s.io] Resources:[ingresses] ResourceNames:[] NonResourceURLs:[]}
                                                      {Verbs:[get] APIGroups:[] Resources:[] ResourceNames:[] NonResourceURLs:[/metrics /metrics/cadvisor]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus serverside-applied
2026-06-15T08:18:24+01:00  apiextensions.k8s.io       CustomResourceDefinition              prometheuses.monitoring.coreos.com             Synced
2026-06-15T08:18:24+01:00                              ConfigMap                monitoring  kube-prometheus-stack-node-cluster-rsrc-use    Synced                       configmap/kube-prometheus-stack-node-cluster-rsrc-use serverside-applied
2026-06-15T08:18:24+01:00  rbac.authorization.k8s.io  ClusterRoleBinding                    kube-prometheus-stack-operator                 Synced
2026-06-15T08:18:25+01:00   apps  Deployment  monitoring  kube-prometheus-stack-kube-state-metrics    Synced  Healthy              deployment.apps/kube-prometheus-stack-kube-state-metrics serverside-applied
2026-06-15T08:18:36+01:00   apps  Deployment  monitoring  kube-prometheus-stack-grafana    Synced  Healthy              deployment.apps/kube-prometheus-stack-grafana serverside-applied

Name:               argocd/monitoring-stack-staging
Project:            monitoring
Server:             https://kubernetes.default.svc
Namespace:          monitoring
URL:                https://127.0.0.1:8080/applications/monitoring-stack-staging
Sources:
- Repo:             https://prometheus-community.github.io/helm-charts
  Target:           65.5.0
  Helm Values:      $values/helm/monitoring-stack/values-staging.yaml
- Repo:             https://github.com/FlameGreat-1/eTradie.git
  Target:           main
  Ref:              values
SyncWindow:         Sync Allowed
Sync Policy:        Automated (Prune)
Sync Status:        Synced to 65.5.0
Health Status:      Healthy


GROUP                         KIND                      NAMESPACE   NAME                                                     STATUS     HEALTH  HOOK     MESSAGE
                              Namespace                             monitoring                                               Running    Synced           namespace/monitoring serverside-applied
                              ServiceAccount            monitoring  kube-prometheus-stack-admission                          Succeeded          PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     ClusterRole               monitoring  kube-prometheus-stack-admission                          Succeeded          PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     ClusterRoleBinding        monitoring  kube-prometheus-stack-admission                          Succeeded          PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     Role                      monitoring  kube-prometheus-stack-admission                          Succeeded          PreSync  kube-prometheus-stack-admission created
rbac.authorization.k8s.io     RoleBinding               monitoring  kube-prometheus-stack-admission                          Succeeded          PreSync  kube-prometheus-stack-admission created
batch                         Job                       monitoring  kube-prometheus-stack-admission-create                   Succeeded          PreSync  job.batch/kube-prometheus-stack-admission-create serverside-applied
                              ServiceAccount            monitoring  kube-prometheus-stack-kube-state-metrics                 Synced                      serviceaccount/kube-prometheus-stack-kube-state-metrics serverside-applied
                              ServiceAccount            monitoring  kube-prometheus-stack-operator                           Synced                      serviceaccount/kube-prometheus-stack-operator serverside-applied
                              ServiceAccount            monitoring  kube-prometheus-stack-prometheus                         Synced                      serviceaccount/kube-prometheus-stack-prometheus serverside-applied
                              ServiceAccount            monitoring  kube-prometheus-stack-grafana                            Synced                      serviceaccount/kube-prometheus-stack-grafana serverside-applied
                              ServiceAccount            monitoring  kube-prometheus-stack-prometheus-node-exporter           Synced                      serviceaccount/kube-prometheus-stack-prometheus-node-exporter serverside-applied
                              Secret                    monitoring  kube-prometheus-stack-grafana                            Synced                      secret/kube-prometheus-stack-grafana serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-kubelet                            Synced                      configmap/kube-prometheus-stack-kubelet serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-pod                  Synced                      configmap/kube-prometheus-stack-k8s-resources-pod serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-grafana-config-dashboards          Synced                      configmap/kube-prometheus-stack-grafana-config-dashboards serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-node-cluster-rsrc-use              Synced                      configmap/kube-prometheus-stack-node-cluster-rsrc-use serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-cluster              Synced                      configmap/kube-prometheus-stack-k8s-resources-cluster serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-alertmanager-overview              Synced                      configmap/kube-prometheus-stack-alertmanager-overview serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-node-rsrc-use                      Synced                      configmap/kube-prometheus-stack-node-rsrc-use serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-nodes-aix                          Synced                      configmap/kube-prometheus-stack-nodes-aix serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-grafana-overview                   Synced                      configmap/kube-prometheus-stack-grafana-overview serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-workload-total                     Synced                      configmap/kube-prometheus-stack-workload-total serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-nodes-darwin                       Synced                      configmap/kube-prometheus-stack-nodes-darwin serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-namespace            Synced                      configmap/kube-prometheus-stack-k8s-resources-namespace serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-grafana                            Synced                      configmap/kube-prometheus-stack-grafana serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-grafana-datasource                 Synced                      configmap/kube-prometheus-stack-grafana-datasource serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-nodes                              Synced                      configmap/kube-prometheus-stack-nodes serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-namespace-by-workload              Synced                      configmap/kube-prometheus-stack-namespace-by-workload serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-namespace-by-pod                   Synced                      configmap/kube-prometheus-stack-namespace-by-pod serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-multicluster         Synced                      configmap/kube-prometheus-stack-k8s-resources-multicluster serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-node                 Synced                      configmap/kube-prometheus-stack-k8s-resources-node serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-apiserver                          Synced                      configmap/kube-prometheus-stack-apiserver serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-prometheus                         Synced                      configmap/kube-prometheus-stack-prometheus serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-pod-total                          Synced                      configmap/kube-prometheus-stack-pod-total serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-cluster-total                      Synced                      configmap/kube-prometheus-stack-cluster-total serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-persistentvolumesusage             Synced                      configmap/kube-prometheus-stack-persistentvolumesusage serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-workload             Synced                      configmap/kube-prometheus-stack-k8s-resources-workload serverside-applied
                              ConfigMap                 monitoring  kube-prometheus-stack-k8s-resources-workloads-namespace  Synced                      configmap/kube-prometheus-stack-k8s-resources-workloads-namespace serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  servicemonitors.monitoring.coreos.com                    Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/servicemonitors.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  prometheusrules.monitoring.coreos.com                    Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/prometheusrules.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  probes.monitoring.coreos.com                             Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/probes.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  podmonitors.monitoring.coreos.com                        Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/podmonitors.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  prometheusagents.monitoring.coreos.com                   Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/prometheusagents.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  alertmanagers.monitoring.coreos.com                      Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/alertmanagers.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  alertmanagerconfigs.monitoring.coreos.com                Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/alertmanagerconfigs.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  thanosrulers.monitoring.coreos.com                       Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/thanosrulers.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  scrapeconfigs.monitoring.coreos.com                      Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/scrapeconfigs.monitoring.coreos.com serverside-applied
apiextensions.k8s.io          CustomResourceDefinition  monitoring  prometheuses.monitoring.coreos.com                       Succeeded  Synced           customresourcedefinition.apiextensions.k8s.io/prometheuses.monitoring.coreos.com serverside-applied
rbac.authorization.k8s.io     ClusterRole               monitoring  kube-prometheus-stack-prometheus                         Succeeded  Synced           clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus reconciled. reconciliation required create
                              missing rules added:
                                           {Verbs:[get list watch] APIGroups:[] Resources:[nodes nodes/metrics services endpoints pods] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get list watch] APIGroups:[discovery.k8s.io] Resources:[endpointslices] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get list watch] APIGroups:[networking.k8s.io] Resources:[ingresses] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get] APIGroups:[] Resources:[] ResourceNames:[] NonResourceURLs:[/metrics /metrics/cadvisor]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus serverside-applied
rbac.authorization.k8s.io     ClusterRole  monitoring  kube-prometheus-stack-operator  Succeeded  Synced    clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-operator reconciled. reconciliation required create
                              missing rules added:
                                           {Verbs:[*] APIGroups:[monitoring.coreos.com] Resources:[alertmanagers alertmanagers/finalizers alertmanagers/status alertmanagerconfigs prometheuses prometheuses/finalizers prometheuses/status prometheusagents prometheusagents/finalizers prometheusagents/status thanosrulers thanosrulers/finalizers thanosrulers/status scrapeconfigs servicemonitors podmonitors probes prometheusrules] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[*] APIGroups:[apps] Resources:[statefulsets] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[*] APIGroups:[] Resources:[configmaps secrets] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[list delete] APIGroups:[] Resources:[pods] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get create update delete] APIGroups:[] Resources:[services services/finalizers endpoints] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[list watch] APIGroups:[] Resources:[nodes] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get list watch] APIGroups:[] Resources:[namespaces] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[patch create] APIGroups:[] Resources:[events] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get list watch] APIGroups:[networking.k8s.io] Resources:[ingresses] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get] APIGroups:[storage.k8s.io] Resources:[storageclasses] ResourceNames:[] NonResourceURLs:[]}
                                           {Verbs:[get create list watch update delete] APIGroups:[discovery.k8s.io] Resources:[endpointslices] ResourceNames:[] NonResourceURLs:[]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-operator serverside-applied
rbac.authorization.k8s.io     ClusterRole  monitoring  kube-prometheus-stack-grafana-clusterrole  Succeeded  Synced    clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrole reconciled. reconciliation required create
                              missing rules added:
                                           {Verbs:[get watch list] APIGroups:[] Resources:[configmaps secrets] ResourceNames:[] NonResourceURLs:[]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrole serverside-applied
rbac.authorization.k8s.io     ClusterRole  monitoring  kube-prometheus-stack-kube-state-metrics  Succeeded  Synced    clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics reconciled. reconciliation required create
                              missing rules added:
                                                  {Verbs:[list watch] APIGroups:[certificates.k8s.io] Resources:[certificatesigningrequests] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[configmaps] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[batch] Resources:[cronjobs] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[extensions apps] Resources:[daemonsets] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[extensions apps] Resources:[deployments] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[endpoints] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[autoscaling] Resources:[horizontalpodautoscalers] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[extensions networking.k8s.io] Resources:[ingresses] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[batch] Resources:[jobs] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[coordination.k8s.io] Resources:[leases] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[limitranges] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[admissionregistration.k8s.io] Resources:[mutatingwebhookconfigurations] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[namespaces] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[networking.k8s.io] Resources:[networkpolicies] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[nodes] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[persistentvolumeclaims] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[persistentvolumes] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[policy] Resources:[poddisruptionbudgets] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[pods] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[extensions apps] Resources:[replicasets] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[replicationcontrollers] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[resourcequotas] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[secrets] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[] Resources:[services] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[apps] Resources:[statefulsets] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[storage.k8s.io] Resources:[storageclasses] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[admissionregistration.k8s.io] Resources:[validatingwebhookconfigurations] ResourceNames:[] NonResourceURLs:[]}
                                                  {Verbs:[list watch] APIGroups:[storage.k8s.io] Resources:[volumeattachments] ResourceNames:[] NonResourceURLs:[]}. clusterrole.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics serverside-applied
rbac.authorization.k8s.io     ClusterRoleBinding  monitoring  kube-prometheus-stack-prometheus  Succeeded  Synced    clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus reconciled. reconciliation required create
                              missing subjects added:
                                                  {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-prometheus Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-prometheus serverside-applied
rbac.authorization.k8s.io     ClusterRoleBinding  monitoring  kube-prometheus-stack-grafana-clusterrolebinding  Succeeded  Synced    clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrolebinding reconciled. reconciliation required create
                              missing subjects added:
                                                  {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-grafana Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana-clusterrolebinding serverside-applied
rbac.authorization.k8s.io     ClusterRoleBinding  monitoring  kube-prometheus-stack-operator  Succeeded  Synced    clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-operator reconciled. reconciliation required create
                              missing subjects added:
                                                  {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-operator Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-operator serverside-applied
rbac.authorization.k8s.io     ClusterRoleBinding  monitoring  kube-prometheus-stack-kube-state-metrics  Succeeded  Synced    clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics reconciled. reconciliation required create
                              missing subjects added:
                                           {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-kube-state-metrics Namespace:monitoring}. clusterrolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-kube-state-metrics serverside-applied
rbac.authorization.k8s.io     Role         monitoring  kube-prometheus-stack-grafana  Synced      role.rbac.authorization.k8s.io/kube-prometheus-stack-grafana reconciled. reconciliation required create. role.rbac.authorization.k8s.io/kube-prometheus-stack-grafana serverside-applied
rbac.authorization.k8s.io     RoleBinding  monitoring  kube-prometheus-stack-grafana  Synced      rolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana reconciled. reconciliation required create
                              missing subjects added:
                                                              {Kind:ServiceAccount APIGroup: Name:kube-prometheus-stack-grafana Namespace:monitoring}. rolebinding.rbac.authorization.k8s.io/kube-prometheus-stack-grafana serverside-applied
                              Service                         monitoring  kube-prometheus-stack-prometheus-node-exporter    Synced     Healthy    service/kube-prometheus-stack-prometheus-node-exporter serverside-applied
                              Service                         monitoring  kube-prometheus-stack-prometheus                  Synced     Healthy    service/kube-prometheus-stack-prometheus serverside-applied
                              Service                         monitoring  kube-prometheus-stack-grafana                     Synced     Healthy    service/kube-prometheus-stack-grafana serverside-applied
                              Service                         monitoring  kube-prometheus-stack-kube-state-metrics          Synced     Healthy    service/kube-prometheus-stack-kube-state-metrics serverside-applied
                              Service                         monitoring  kube-prometheus-stack-operator                    Synced     Healthy    service/kube-prometheus-stack-operator serverside-applied
apps                          DaemonSet                       monitoring  kube-prometheus-stack-prometheus-node-exporter    Synced     Healthy    daemonset.apps/kube-prometheus-stack-prometheus-node-exporter serverside-applied
apps                          Deployment                      monitoring  kube-prometheus-stack-kube-state-metrics          Synced     Healthy    deployment.apps/kube-prometheus-stack-kube-state-metrics serverside-applied
apps                          Deployment                      monitoring  kube-prometheus-stack-grafana                     Synced     Healthy    deployment.apps/kube-prometheus-stack-grafana serverside-applied
apps                          Deployment                      monitoring  kube-prometheus-stack-operator                    Synced     Healthy    deployment.apps/kube-prometheus-stack-operator serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  coredns                                           Synced                servicemonitor.monitoring.coreos.com/coredns serverside-applied
admissionregistration.k8s.io  ValidatingWebhookConfiguration  monitoring  kube-prometheus-stack-admission                   Succeeded  Synced     validatingwebhookconfiguration.admissionregistration.k8s.io/kube-prometheus-stack-admission serverside-applied
admissionregistration.k8s.io  MutatingWebhookConfiguration    monitoring  kube-prometheus-stack-admission                   Succeeded  Synced     mutatingwebhookconfiguration.admissionregistration.k8s.io/kube-prometheus-stack-admission serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-kube-state-metrics          Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-kube-state-metrics serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-operator                    Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-operator serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-grafana                     Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-grafana serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-apiserver                   Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-apiserver serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-prometheus                  Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-prometheus serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-kubelet                     Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-kubelet serverside-applied
monitoring.coreos.com         Prometheus                      monitoring  kube-prometheus-stack-prometheus                  Synced     Healthy    prometheus.monitoring.coreos.com/kube-prometheus-stack-prometheus serverside-applied
monitoring.coreos.com         ServiceMonitor                  monitoring  kube-prometheus-stack-prometheus-node-exporter    Synced                servicemonitor.monitoring.coreos.com/kube-prometheus-stack-prometheus-node-exporter serverside-applied
admissionregistration.k8s.io  MutatingWebhookConfiguration                kube-prometheus-stack-admission                   Synced
admissionregistration.k8s.io  ValidatingWebhookConfiguration              kube-prometheus-stack-admission                   Synced
apiextensions.k8s.io          CustomResourceDefinition                    alertmanagerconfigs.monitoring.coreos.com         Synced
apiextensions.k8s.io          CustomResourceDefinition                    alertmanagers.monitoring.coreos.com               Synced
apiextensions.k8s.io          CustomResourceDefinition                    podmonitors.monitoring.coreos.com                 Synced
apiextensions.k8s.io          CustomResourceDefinition                    probes.monitoring.coreos.com                      Synced
apiextensions.k8s.io          CustomResourceDefinition                    prometheusagents.monitoring.coreos.com            Synced
apiextensions.k8s.io          CustomResourceDefinition                    prometheuses.monitoring.coreos.com                Synced
apiextensions.k8s.io          CustomResourceDefinition                    prometheusrules.monitoring.coreos.com             Synced
apiextensions.k8s.io          CustomResourceDefinition                    scrapeconfigs.monitoring.coreos.com               Synced
apiextensions.k8s.io          CustomResourceDefinition                    servicemonitors.monitoring.coreos.com             Synced
apiextensions.k8s.io          CustomResourceDefinition                    thanosrulers.monitoring.coreos.com                Synced
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-grafana-clusterrole         Synced
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-kube-state-metrics          Synced
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-operator                    Synced
rbac.authorization.k8s.io     ClusterRole                                 kube-prometheus-stack-prometheus                  Synced
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-grafana-clusterrolebinding  Synced
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-kube-state-metrics          Synced
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-operator                    Synced
rbac.authorization.k8s.io     ClusterRoleBinding                          kube-prometheus-stack-prometheus                  Synced