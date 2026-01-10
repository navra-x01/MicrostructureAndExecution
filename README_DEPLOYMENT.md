# Deployment Guide: Market Microstructure Simulator

This guide explains how to deploy the Market Microstructure Simulator to Streamlit Cloud so that anyone can access it via a web browser.

## Prerequisites

1. **GitHub Account**: You need a GitHub account (free)
2. **Streamlit Cloud Account**: Sign up at [https://streamlit.io/cloud](https://streamlit.io/cloud) (free for public repos)
3. **Git Repository**: Your project should be in a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### Step 1: Prepare Your Repository

1. **Ensure all files are committed**:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   ```

2. **Push to GitHub**:
   ```bash
   git push origin main
   ```
   (Replace `main` with your branch name if different)

### Step 2: Deploy to Streamlit Cloud

1. **Sign in to Streamlit Cloud**:
   - Go to [https://share.streamlit.io/](https://share.streamlit.io/)
   - Sign in with your GitHub account

2. **Create a New App**:
   - Click "New app" button
   - Select your repository from the dropdown
   - Select the branch (usually `main` or `master`)
   - Set the **Main file path** to: `streamlit_app.py`
   - Click "Deploy!"

3. **Wait for Deployment**:
   - Streamlit Cloud will automatically:
     - Install dependencies from `requirements.txt`
     - Build your app
     - Deploy it to a public URL
   - This usually takes 1-2 minutes

4. **Access Your App**:
   - Once deployed, you'll get a public URL like:
     `https://your-app-name.streamlit.app`
   - Share this URL with anyone!

## Project Structure for Deployment

Your project should have the following structure:

```
project2/
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── dashboard/
│   └── app.py               # Main dashboard code
├── streamlit_app.py         # Entry point for Streamlit Cloud
├── requirements.txt         # Python dependencies
├── main.py                  # Backtest engine
├── config.py                # Configuration
└── ... (other project files)
```

## Key Files Explained

### `streamlit_app.py`
This is the entry point that Streamlit Cloud looks for. It imports and runs your dashboard.

### `.streamlit/config.toml`
Configuration file for Streamlit settings (theme, server settings, etc.)

### `requirements.txt`
Lists all Python dependencies. Streamlit Cloud installs these automatically.

## Features Available After Deployment

Once deployed, users can:

1. **Interactive Dashboard**:
   - View order book in real-time
   - See price charts and signals
   - Monitor PnL metrics

2. **Run Simulations**:
   - Upload custom CSV data files
   - Run full backtests
   - Adjust parameters (initial cash, etc.)

3. **Download Results**:
   - Download trades as CSV
   - Download signals as CSV
   - Download PnL history as CSV
   - Download metrics as JSON

## Troubleshooting

### App Won't Deploy

1. **Check `requirements.txt`**:
   - Ensure all dependencies are listed
   - Check for version conflicts
   - Make sure versions are compatible

2. **Check `streamlit_app.py`**:
   - Ensure it exists in the root directory
   - Verify it imports the dashboard correctly

3. **Check Logs**:
   - In Streamlit Cloud dashboard, click on your app
   - Check the "Logs" tab for error messages

### Common Issues

**Import Errors**:
- Make sure all Python files use relative imports correctly
- Check that `__init__.py` files exist in package directories

**File Not Found Errors**:
- Use relative paths (not absolute paths)
- For temporary files, use `tempfile` module (already implemented)

**Memory Issues**:
- Large datasets may cause memory issues
- Consider limiting data size or using data sampling

## Updating Your Deployment

To update your deployed app:

1. Make changes to your code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update app"
   git push origin main
   ```
3. Streamlit Cloud will automatically detect changes and redeploy
4. Wait 1-2 minutes for the update to complete

## Custom Domain (Optional)

Streamlit Cloud allows you to use a custom domain:

1. Go to your app settings in Streamlit Cloud
2. Click "Settings"
3. Scroll to "Custom domain"
4. Follow the instructions to set up your domain

## Security Considerations

- **Public Access**: By default, Streamlit Cloud apps are publicly accessible
- **Data Privacy**: Don't upload sensitive data files
- **Rate Limiting**: Streamlit Cloud has rate limits for free tier
- **Resource Limits**: Free tier has CPU and memory limits

## Cost

- **Free Tier**: Available for public GitHub repositories
- **Team Tier**: Available for private repos (paid)

## Support

If you encounter issues:

1. Check Streamlit Cloud documentation: [https://docs.streamlit.io/streamlit-cloud](https://docs.streamlit.io/streamlit-cloud)
2. Check Streamlit Cloud status: [https://status.streamlit.io/](https://status.streamlit.io/)
3. Review your app logs in the Streamlit Cloud dashboard

## Next Steps

After deployment:

1. Test all features in the deployed app
2. Share the URL with users
3. Monitor usage and performance
4. Gather feedback and iterate

---

**Happy Deploying! 🚀**
