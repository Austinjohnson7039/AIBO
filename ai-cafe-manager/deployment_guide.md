# 🚀 How to Deploy to Hugging Face (2 Minutes)

Follow these steps to put your AI Cafe Manager live on the web!

### 1. Create your Space
1.  Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2.  **Space Name**: `ai-cafe-manager` (or anything you like).
3.  **SDK**: Select **Docker**.
4.  **Template**: Select **Blank**.
5.  **Visibility**: Select **Private** (recommended) or Public.

### 2. Add your Secrets (CRITICAL)
Before you upload the code, you must tell Hugging Face your "Secret" keys so the app can talk to the database and Groq.
1.  In your new Space, go to the **Settings** tab.
2.  Scroll down to **Variables and secrets**.
3.  Click **New secret** for each of these:
    - `GROQ_API_KEY`: (Your gsk_... key)
    - `DATABASE_URL`: (Your postgres://... key)
    - `APP_USERNAME`: `admin`
    - `APP_PASSWORD`: `cafe123`

### 3. Upload your Code
1.  Initialize a Git repo in your current folder:
    ```bash
    git init
    git add .
    git commit -m "Initial cloud commit"
    ```
2.  Add Hugging Face as a remote (you'll see the command on your Space page).
3.  **Push** the code: `git push --force huggingface main`.

---

## 🔐 Security Check
Your app now has a **Login Screen**. 
- **Default Username**: `admin`
- **Default Password**: `cafe123`

> [!TIP]
> Once you are logged in, you can access your dashboard from any phone, anywhere in the world! 🌍
