#!/bin/bash
# Rainference Cluster Bootstrap Script
# Provisions a bare-metal Kubernetes cluster (v1.29) with NVIDIA GPU support on Ubuntu 22.04.

set -e

echo "========================================="
echo " Rainference Kubernetes Cluster Bootstrap "
echo "========================================="

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "[1/7] Disabling swap..."
swapoff -a
sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

echo "[2/7] Installing prerequisites and containerd..."
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gpg software-properties-common

# Configure containerd modules
cat <<EOF | tee /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF
modprobe overlay
modprobe br_netfilter

# Configure sysctl params
cat <<EOF | tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables  = 1
net.ipv4.ip_forward                 = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sysctl --system

apt-get install -y containerd
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml >/dev/null
sed -i 's/SystemdCgroup \= false/SystemdCgroup \= true/g' /etc/containerd/config.toml
systemctl restart containerd
systemctl enable containerd

echo "[3/7] Installing Kubernetes components (v1.29)..."
# Add Kubernetes apt repository
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

echo "[4/7] Installing NVIDIA drivers (v535)..."
apt-get install -y ubuntu-drivers-common
ubuntu-drivers install nvidia:535

echo "[5/7] Installing NVIDIA Container Toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt-get update
apt-get install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=containerd
systemctl restart containerd

echo "[6/7] Initializing Kubernetes Cluster..."
# Initialize cluster with Pod CIDR suitable for Flannel
kubeadm init --pod-network-cidr=10.244.0.0/16

# Configure kubectl for the root user
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# Remove taint to allow scheduling on the master node (since this is a single-node cluster)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

echo "[7/7] Installing CNI (Flannel)..."
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

echo "========================================="
echo " Bootstrap Complete!"
echo " A reboot may be required to fully load the NVIDIA drivers."
echo " After reboot, you can run: bash k8s-setup.sh --skip-init"
echo "========================================="
