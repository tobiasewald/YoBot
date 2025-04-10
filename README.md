
---

### **Complete Project: YoBot with Humor, Trivy Analysis, and Deployment**

---

Precondtion: Docker for Desktop and running k8s-Cluster (local) 

#### **1. ArgoCD deloyment and Connection**

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl port-forward svc/argocd-server -n argocd 8088:443

kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d
```

---

#### **2. Create Discord-Channel with WEBHOOK **
1. Open Your Discord Server
Go to your Discord server where you want to add the webhook.

2. Create a Channel
Click the "+" next to Text Channels
Choose Text Channel
Click Create Channel

3. Create a Webhook
Go to Server Settings → Integrations
Click on Webhooks
Click New Webhook
Set:
Name: YoBot-Webhook (or anything funny 😄)
Channel: Select your channel
Avatar: Optional (make it meme-worthy if you want)
Click Copy Webhook URL (you'll need this for .env or your app)
Click Save

4. Store the Webhook in .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/yourwebhooktoken

---

#### **3. Let's run **
```bash
1. go on yobot via shell
2. run command: python main.py
3. See your message in discord channel

```