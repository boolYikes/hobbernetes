*WIP*
# Kubernetes in General
I'm not an expert nor am I here to teach!</br>
This doc, in its entirety, is to serve as a self-reminder!
## Architecture
![alt text](image-2.png)
## ...
# Experiments
## Environment
- Master node: Ubuntu 24.04 server on Hyper-V on Windows 10 Pro
- Worker node: Ubuntu 24.04 server on a baremetal, dedicated server
- Networking: All nodes on WAN connection behind a simple router.
## Setup Overview
## The Backbone
### I. Hyper-V
i. Host setup
- This will be the master node.
- Req: Win 10 Pro or NT?
- In Bios, enable virtualization(method varies).
- Enable the feature on Hyper Visor Manager, restart PC

ii. VM
- *External Switch* for the network adaptor
- *Dynamic Memory* minimum set to 4GB
- *CPUs* set to at least 2: check `htop` or `lscpu` to confirm the number of cpus. If the setting's not working, refer to Hyper-V docs.
### II. Host machine settings
Applies to master and worker nodes alike from here on out!</br>
i. Host config</br>
Get the network interface's ipv4 address of ALL NODES. Mines are 192.168.0.8 and 100.</br>
`sudo vi /etc/hosts`</br>
then, add:
```plaintext
...
192.168.0.8 master
192.168.0.100 worker-01
...
```
ii. Firewalls</br>
Disable the frontend firewall. For Redhat base OS, it's firewalld.</br>
```bash
sudo ufw disable
sudo systemctl stop ufw
sudo systemctl disable ufw
sudo systemctl mask --now ufw
```
then,
```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
```
then,
```bash
sudo sysctl --system
```


### III. Docker
*DO NOT COPY PASTE THE WHOLE BLOCK* LOL
```bash
# DO NOT remove containerd. it might ship as default on you distro

# check for old packages
 for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
# and then, clean it up
sudo rm -rf /var/lib/docker 
# update repo and then install
sudo apt-get update
sudo apt-get install ca-certificates curl
# secrets
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
# install the package
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
# then"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```
### IV. CRI-Dockerd
<strong>1.This is needed unless you hate Docker</strong></br>
*CHECK YOUR OS COMPAT!!* Mine is Ubuntu 24.04 noble</br>
Install Go lang : https://go.dev/doc/install</br>
An excerpt from the Mirantis doc.</br>
```shell
git clone https://github.com/Mirantis/cri-dockerd.git
# ONCE DONE,
cd cri-dockerd
ARCH=amd64 make cri-dockerd
sudo mkdir -p /usr/local/bin
sudo install -o root -g root -m 0755 cri-dockerd /usr/local/bin/cri-dockerd
sudo install packaging/systemd/* /etc/systemd/system
sudo sed -i -e 's,/usr/bin/cri-dockerd,/usr/local/bin/cri-dockerd,' /etc/systemd/system/cri-docker.service
sudo systemctl daemon-reload
sudo systemctl enable --now cri-docker.socket
```
then, inside `sudo nano /etc/systemd/system/multi-user.target.wants/cri-docker.service` edit line,</br>
```yaml
ExecStart=/usr/local/bin/cri-dockerd --container-runtime-endpoint fd:// --network-plugin=cni --pod-cidr=10.244.0.0/16
```
then,</br>
check `sudo nano /etc/crictl.yaml` if `runtime-endpoint` is set to `unix:///var/run/cri-dockerd.sock`. If not, add it.</br>
then finally, `sudo systemctl daemon-reload`</br>
<strong>2. DO THIS ONLY IF `docker info | grep Cgroup` shows `cgroupfs`, not `systemd`</strong></br>
In this file:(It could pre-exist or be empty)</br>
`sudo nano /etc/docker/daemon.json`</br>
add this code:</br>
`{
  "exec-opts": ["native.cgroupdriver=systemd"]
}`</br>
then, execute:</br>
`sudo systemctl restart docker`</br>
and finally, </br>
`sudo chmod 666 /var/run/cri-dockerd.sock`</br>
### V. Kubes
```bash
# update repos
sudo apt-get update
# install dependencies
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
# secrets
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
# add repo
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
# update repo
sudo apt-get update
# install cores
sudo apt-get install -y kubelet kubeadm kubectl
# version fixed
sudo apt-mark hold kubelet kubeadm kubectl
```
### IV. Masternode Init
    a. Decide which network add-on to use.
    b. The network add-on will have instructions on which CIDR to use.
    c. Use that to specify init's CIDR parameter.
    d. If using Docker Engine, don't forget the Unix socket parameter for cri-dockerd
    e. Always do dry run first so you don't have to reset and start all over again ...
i. 
`crictl config --set runtime-endpoint=unix:///var/run/cri-dockerd.sock`</br>
ii. `sudo systemctl start cri-docker`</br>
iii. `sudo systemctl enable cri-docker`</br>
iv. Switch to root for ease of use `sudo -i`</br>
v. `sudo sed -i '/swap/d' /etc/fstab` and then *reboot*</br>
vi. Init CP: Initially i was gonna use Flannel hence the cidr block but it doesn't matter now that i'm using Calico. Just be consistent.</br>
```bash
sudo kubeadm init \
--cri-socket unix:///var/run/cri-dockerd.sock \
--pod-network-cidr 10.244.0.0/16
```
This'll output instructions on how to join nodes. Write down the token and hash. They expire after 24h. We'll talk about this later. (See 'Joining a node')
### V. Kubectl config
```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```
### VI. Network plugin

**<< RESTART HERE. WILL USE FLANNEL THIS TIME DUE TO METALLB ISSUE**

`kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/tigera-operator.yaml`</br>
then, </br>

`wget https://raw.githubusercontent.com/projectcalico/calico/v3.29.0/manifests/custom-resources.yaml`</br>
then,</br>

`sudo curl -L https://github.com/projectcalico/calico/releases/download/v3.29.0/calicoctl-linux-amd64 -o /usr/local/bin/calicoctl`</br>

`sudo chmod +x /usr/local/bin/calicoctl`</br>

`nano custom-resources.yaml`</br>
and edit line: </br>

`cidr: 10.244.0.0/16`</br>
confirm pods running:</br>

`watch kubectl get pods -n calico-system`</br>
"taint" nodes, which means to make a node available for pods</br>
`kubectl taint nodes --all node-role.kubernetes.io/control-plane-`</br>
confirm node exposure:</br>
`kubectl get nodes -o wide`</br>

## Joining a node
### I. Follow the above guide
- Not to the tee though. Always crosscheck with your environment.
- Follow up until you reach the `kubeadm init` part.
### II. The token
1. <strong>FROM YOUR MASTER NODE</strong>, If you've been a good boi/gal and wrote down the token and hash, `skip 2. to 4`.
2. If 24h hasn't passed since you have created the token: `sudo kubeadm token list` and write it down.
3. If it's expired, `sudo kubeadm token create` and keep a memo.
4. To get the hash, `sudo cat /etc/kubernetes/pki/ca.crt | openssl x509 -pubkey  | openssl rsa -pubin -outform der 2>/dev/null | openssl dgst -sha256 -hex | sed 's/^.* //'`
5. <strong>FROM YOUR WORKER NODE</strong>, Join: </br>
`sudo kubeadm join --token <token> <cp-host>:<cp-port> --discovery-token-ca-cert-hash sha256:<hash>`
6. <strong>IF YOU GET THE multiple container runtime socket ERROR</strong> follow 7. ~ 8.
7. `sudo nano pick-a-name.yaml` and then,
```yaml
apiVersion: kubeadm.k8s.io/v1beta4
kind: JoinConfiguration
discovery:
  bootstrapToken:
    apiServerEndpoint: <master-ip>:6443
    token: <token>
    caCertHashes:
    - sha256:<ca-cert-hash>
nodeRegistration:
  criSocket: unix:///var/run/cri-dockerd.sock
```
8. `sudo kubeadm join --config pick-a-name.yaml`
9. Confirm that it has joined the mob: The cp has to propagate Calico and other things so be patient
![alt text](image.png)
### III. Role
1. Initially the worker node's role is labeled none. I'm still investigating if that's the default or not. But I went on to modifying it anyways: `kubectl label nodes <worker-name> node-role.kubernetes.io/worker=worker`</br>
2. The syntax means to asign *'worker'* label to the nodes that have the *'role key'* of a name *'node-role.kubernetes.io/worker'*
---
## Ready to Deploy
But hold your horses...
### I. Persistnet Volumes
Build me a friggin castle</br>
I'm not provisioning db as a service(doesn't have to be dynamic) so i'll just use local storage. I maybe digging my own grave but hey it's just a sandbox right?</br>
<strong>i. Define a storage class:</strong></br>
This is merely a definition of  provisioning method, not an actual volume: </br>

`nano storageclass-local.yaml`</br>
add:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
```

then, `kubectl apply -f storageclass-local.yaml`</br>
<strong>ii. Define persistent volume obejct:</strong></br>
This is the actual resource definition. This specific PV will be used by a web server pod that has a Mongo DB instance in it:</br>

`nano mongo-pv.yaml` then,

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mongo-pv
spec:
  capacity:
    storage: 5Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: local-storage
  claimRef:
    name: mongo-pvc
    namespace: express-mongodb
  local:
    path: /lab/mnt/pvs/mongo
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - worker-01
```

then, `kubectl apply -f mongo-pv.yaml`</br>
<strong>iii. Service namespace:</strong></br>
It doesn't sit right to place it here but...:</br>

`nano namespace-express-mongo.yaml` then, </br>

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: express-mongodb 
# almost feels wrong that it's so short?
```

then, `kubectl apply -f namespace-express-mongo.yaml`</br>
<strong>iv. Resource claim object:</strong></br>
Pods will use this to request volume resources:</br>

`nano mongo-pvc.yaml` then,</br>

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mongo-pvc
  namespace: express-mongodb
spec:
  storageClassName: local-storage
  accessModes:
    - ReadWriteOnce
  volumeName: mongo-pv
  resources:
    requests:
      storage: 5Gi
```

### II. Install Helm
It's a package manager for K8S: </br>

```bash
wget https://get.helm.sh/helm-v3.16.3-linux-amd64.tar.gz
tar -xvzf helm-v3.16.3-linux-amd64.tar.gz
mv linux-amd64 helm # for readability
echo "export PATH=$PATH:$(pwd)/helm" >> ~/.bashrc # I use _aliases for church and state reasons 
source ~/.bashrc 
# helm is ready
```

### III. Gateway
Objective: Add a gateway for pods, make a deployment manifest, and expose via gateway using httproute</br>
<strong>i. Baseline(?) Gateway API</strong></br>
It adds the Gateway, HTTPRoute kinds and more</br>

`kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml`
<strong>ii. Gateway API Resources</strong></br> 
The Custom Resource `Definition` or 'CRD'...</br>

`kubectl kustomize "https://github.com/nginxinc/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v1.5.0" | kubectl apply -f -`
<strong>iii. Gateway controller: This is the actual deployment</strong></br>

`helm install --wait ngf oci://ghcr.io/nginxinc/charts/nginx-gateway-fabric --create-namespace -n nginx-gateway`
</br>

<strong>iv. MetalLB</strong></br>
At this point, my `kubectl get svc nginx-gateway`, output showed that the external ip was 'pending'. It's bc my cluster is on baremetal, not a IaaS like AWS or GCP or Azure. MetalLB handles this.</br>
![alt text](image-3.png)

`sudo apt install iptables-persistent`

`sudo iptables -A INPUT -p tcp --dport 7946 -j ACCEPT`</br>
`sudo iptables -A INPUT -p udp --dport 7946 -j ACCEPT` then,</br>
<< << << from here
`kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml`</br>

```bash
calicoctl create -f - <<EOF
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceLoadBalancerIPs:
  - cidr: 10.244.0.0/16
EOF
```

`kubectl delete daemonset speaker -n metallb-system`</br>

This should let the LB work on my baremetal and It won't conflict with Calico</br>
**This setup should be later varified because**</br>
1. It uses layer 2 mode but disables speaker 

<strong>v. Gateway and Routing</strong></br>

`nano gateway.yaml`</br>

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: nginx-gateway
  namespace: nginx-gateway
spec:
  type: LoadBalancer
  gatewayClassName: nginx
  listeners:
    - name: http
      protocol: HTTP
      port: 80
```

`kubectl apply -f gateway.yaml`</br>

In `nano httproute.yaml`,</br>

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:

```

**Validate first** with `kubectl apply --validate='strict' -f xx.yaml`</br>

## TODOs
### Pending
- [ ] tainted love
- [ ] kubectl drain for gracefule shutdown
- [ ] investigate autoscaling mechanism
- [ ] about service account
- [ ] object definition files(.yaml) management
### Resolved
- [x] how node certificate redemption is handled?: only used when joining
# Addendum
## I. Custom init config
THESE WERE USED RIGHT BEFORE INIT</br>
vi.
```yaml
# write a config anywhere
apiVersion: kubeadm.k8s.io/v1beta3
kind: InitConfiguration
nodeRegistration:
  criSocket: /var/run/cri-dockerd.sock
```
```bash
# run this to render the config up-to-date\
sudo kubeadm config migrate --old-config old.yaml --new-config new.yaml
```
```yaml
# and open new.yaml, add under the networking section under the clusterconfig:
podSubnet: 10.244.0.0/16
# and add new lines at the bottom, including the hypens
---
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
containerRuntimeEndpoint: unix:///var/run/cri-dockerd.sock
```
vii. Kubelet related (prolly should be set after init or join is done)
```bash
## pause image : this seems to be deprecated
# kubelet --pod-infra-container-image=registry.k8s.io/pause:3.10
## In here:
sudo nano /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
## edit line:
Environment="KUBELET_EXTRA_ARGS=--pod-infra-container-image=registry.k8s.io/pause:3.9"
```
viii. The core
```bash
kubeadm init \
# --dry-run \ # for testing
--config "path/to/previously/made/new.yaml" \
```
- On failure for some reason, fix the issue and `sudo kubeadm reset` and then do over
- Set up kubelet, kubectl
- Replicate the process on other node, this time with `join`

## II. Migrating UFW rules
### NO I DID NOT WANT TO DO IT PROGRAMMATICALLY 😣
1. `sudo ufw status` to check your rules.</br>
2. If a rule states `5432/tcp ALLOW Anywhere` then, `sudo iptables -A INPUT -p tcp --dport 5432 -j ACCEPT`
3. If a rule states `5432 ALLOW 123.1.0.0/16 -j ACCEPT` then, `sudo iptables -A INPUT -p tcp --deport 5432 -s 123.1.0.0/16 -j ACCEPT`
4. Same rule goes for ip6tables for ipv6 rules.

## III. Node control
1. To access the CP api from outside the cluster,
2. Install kubectl on the client machine. *root login should be allowed* via sshd-config
3. From the client, `scp root@<cp-host>:/etc/kubernetes/admin.conf .`
4. Edit `/etc/hosts` file to include ip mapping (in this case, `192.168.0.8 master`). On windows, its located in `C:\Windows\System32\drivers\etc\hosts`
5. Test it: `kubectl --kubeconfig ./admin.conf get nodes`
6. Run a proxy from the client: `kubectl --kubeconfig ./admin.conf proxy`
7. Access the api from local: `http://localhost:8001/api/v1`
![alt text](image-1.png)
8. But it's best to use regular user credentials. I'll continue this one the service account subject. 
Also See quote from the official site:
*Note: ......
*The admin.conf file gives the user superuser privileges over the cluster. This file should be used sparingly. For normal users, it's recommended to generate an unique credential to which you grant privileges. You can do this with the `kubeadm kubeconfig user --client-name` command. That command will print out a KubeConfig file to STDOUT which you should save to a file and distribute to your user. After that, grant privileges by using `kubectl create (cluster)rolebinding`.*

