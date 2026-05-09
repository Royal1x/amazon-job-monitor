# Amazon Warehouse Job Monitor

This beginner-friendly Python project watches Amazon warehouse job listings for:

- **Liverpool, New York**
- **East Syracuse, New York**

It will:

- check Amazon automatically every second by default
- look only for Liverpool, NY and East Syracuse, NY warehouse-style jobs
- send a **WhatsApp message**
- place an **automated phone call**
- avoid duplicate alerts for the same job
- print `No new jobs found` when nothing new appears

## Files in this project

- `main.py` - the job monitor script
- `requirements.txt` - the Python packages you need
- `.env` - your local Twilio settings
- `.env.example` - a safe template for local or cloud setup
- `.vscode/launch.json` - lets you run the script directly in VS Code
- `test_twilio.py` - sends a test WhatsApp message or test call
- `.github/workflows/amazon-job-monitor.yml` - runs the monitor on GitHub Actions
- `.github/workflows/azure-vm-health.yml` - checks the Azure VM from outside and can auto-restart the monitor service
- `oracle_vm_setup.sh` - sets up the project on an Ubuntu or Debian cloud VM, including Oracle Cloud or Azure
- `seen_jobs.json` - created automatically after the first run
- `tests/test_main.py` - simple helper tests that do not send real alerts

## Which Amazon website it uses

The main Amazon page people use in the browser is:

`https://hiring.amazon.com/app#/jobSearch`

That page is a JavaScript app. Since this project must use `requests` and `BeautifulSoup`, the script reads this official Amazon warehouse HTML page instead:

`https://hiring.amazon.com/search/warehouse-jobs`

This keeps the project simple and beginner-friendly while still monitoring official Amazon warehouse listings.

## How alerts work

This project uses **Twilio** to send:

- a WhatsApp message
- an automated phone call

You need:

- a Twilio account
- a Twilio phone number with voice support
- a phone with WhatsApp installed
- your own phone number

For WhatsApp testing, this project uses the **Twilio Sandbox for WhatsApp**. Your phone must join the sandbox before WhatsApp alerts can arrive.

## Run the project in Visual Studio Code

### 1. Open the folder

Open **Visual Studio Code**, then open:

`/Users/royalpoudel/Documents/Playground`

### 2. Open the terminal in VS Code

In VS Code, click:

- `Terminal`
- `New Terminal`

### 3. Create a virtual environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install the packages

```bash
pip install -r requirements.txt
```

### 5. Add your Twilio settings

This project reads Twilio values from the local `.env` file.

Example:

```env
TWILIO_ACCOUNT_SID="your_account_sid"
TWILIO_AUTH_TOKEN="your_auth_token"
TWILIO_FROM_PHONE="+12345678901"
ALERT_TO_PHONE="+13155551234,+13155550000"
TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
ALERT_TO_WHATSAPP="whatsapp:+13155551234,whatsapp:+13155550000"
CHECK_INTERVAL_SECONDS="1"
```

Use full phone numbers like `+13155551234`.
If you want more than one recipient, separate them with commas.

For WhatsApp numbers, add the `whatsapp:` prefix.

### 6. Join the Twilio WhatsApp sandbox

Open the Twilio Console page for the WhatsApp sandbox and follow the join instructions there.

You usually need to:

- open WhatsApp on your phone
- send the sandbox join code shown in your Twilio Console
- send it to Twilio's sandbox WhatsApp number

The Twilio sandbox sender used by this project is:

`whatsapp:+14155238886`

The join code can change, so read the current one from your Twilio Console before testing.

### 7. Run the script

```bash
python main.py
```

If your computer uses `python3` instead of `python`, run:

```bash
python3 main.py
```

### 8. Run a quick alert test

If you want to send a quick WhatsApp-only test:

```bash
python3 test_twilio.py
```

If you want to label the test with a nearby city, you can do this:

```bash
python3 test_twilio.py --city Rochester
```

If you also want the phone call during a test, add:

```bash
python3 test_twilio.py --with-call
```

### 9. Run it with the VS Code Run button

This project includes a VS Code launch config.

In VS Code:

- open the `Run and Debug` panel
- choose `Run Amazon Job Monitor`
- click the green Run button

VS Code will automatically read the values from `.env`.

### 10. Run the helper tests

These tests do not send real alerts. They only check the small Python helper logic.

```bash
python3 -m unittest discover -s tests
```

## Run it for free on GitHub Actions

This is the easiest free cloud version if you already use GitHub.

Important:

- GitHub Actions scheduled jobs run at most every 5 minutes
- they cannot run every second
- Amazon is currently returning `403 Forbidden` to GitHub-hosted runners for the scrape step
- because of that, this repository keeps the GitHub workflow as a **manual test workflow**, not a live automatic monitor
- this project uses `seen_jobs.json` to remember which jobs were already announced
- the workflow automatically updates `seen_jobs.json` in your repository after each run

### 1. Put this project in a GitHub repository

Create a GitHub repository and upload this project.

### 2. Add your GitHub repository secrets

In your GitHub repository, open:

- `Settings`
- `Secrets and variables`
- `Actions`

Add these repository secrets:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_PHONE`
- `ALERT_TO_PHONE`
- `TWILIO_WHATSAPP_FROM`
- `ALERT_TO_WHATSAPP`

For WhatsApp sandbox testing, `TWILIO_WHATSAPP_FROM` is usually:

```text
whatsapp:+14155238886
```

### 3. Enable the workflow

This project already includes:

- [amazon-job-monitor.yml](/Users/royalpoudel/Documents/Playground/.github/workflows/amazon-job-monitor.yml)

Once you push the project to GitHub, the workflow can run automatically.

Right now it runs any time you manually start it from the GitHub Actions tab.

The separate Azure health workflow can still be useful, though:

- it runs outside Azure, so it can notice when your VM or monitor has trouble
- it sends a WhatsApp warning if the Azure monitor stays down
- if the VM is reachable, it first tries to restart the `amazon-job-monitor` service automatically
- if that restart works, it sends a recovery WhatsApp message instead of a failure alert

### 4. Run your first GitHub test

In your repository:

- open the `Actions` tab
- click `Amazon Job Monitor`
- click `Run workflow`
- turn on `send_test_alert`
- click `Run workflow`

That sends a labeled test WhatsApp message and phone call from GitHub Actions.

### 5. Run a normal one-time monitor check

After the test works, run the workflow again with `send_test_alert` turned off.

This will try one real Amazon check from GitHub Actions.

If Amazon still blocks the GitHub runner, the run will show the `403 Forbidden` message in the logs.

### 6. For true automatic cloud monitoring

The better next host for students is usually **Azure for Students**, because GitHub Education lists Azure student credits and says no credit card is required for eligible students:

- [GitHub Education pack](https://education.github.com/pack)
- [Azure for Students in the GitHub pack](https://education.github.com/pack/redeem/azure-for-students)

## Run it without your Mac using Azure

This project is already set up to run well on an **Ubuntu Azure VM**.

The same [oracle_vm_setup.sh](/Users/royalpoudel/Documents/Playground/oracle_vm_setup.sh) script works on Azure too, because it only needs a normal Ubuntu or Debian server with `sudo`.

Important:

- the current Azure deployment uses a **Spot VM** because the student subscription blocks many normal small VM sizes
- Spot VMs can be evicted by Azure, so they are cheaper but a little less reliable than normal VMs
- Twilio calls and WhatsApp messages can still cost money after your trial balance runs out

### Azure auto-recovery and outage alerts

This project also includes a GitHub Actions backup workflow named `Azure VM Health Check`.

It checks the Azure VM from outside every 5 minutes and:

- tries to restart the `amazon-job-monitor` service automatically if the VM is reachable
- sends a WhatsApp recovery message if that auto-fix works
- sends a WhatsApp outage alert if the monitor still looks down

This is useful because the live Amazon job scraping runs on Azure, while GitHub acts like an outside watcher.

### 1. Create an Ubuntu VM

Create an Ubuntu VM in Azure and allow SSH access.

### 2. Copy this project to the VM

Copy the project folder to your server, including your `.env` file.

### 3. Run the setup script on the VM

```bash
cd ~/amazon-job-monitor
bash oracle_vm_setup.sh
```

### 4. Check that the monitor is running

```bash
sudo systemctl status amazon-job-monitor
sudo journalctl -u amazon-job-monitor -f
```

If it is working, you should see lines like:

```text
Watching Amazon warehouse jobs in Liverpool, NY, East Syracuse, NY...
No new jobs found
```

## Run it without your Mac using Oracle Cloud Always Free

If you want this monitor to keep running when your Mac is off, you can move it to an **Oracle Cloud Always Free** Linux VM.

This project includes [oracle_vm_setup.sh](/Users/royalpoudel/Documents/Playground/oracle_vm_setup.sh) to make that easier.

Important:

- Oracle Cloud can be free
- Twilio calls and WhatsApp messages can still cost money after your trial balance runs out

### 1. Create an Oracle Cloud VM

Create an **Always Free** Ubuntu VM in Oracle Cloud.

Official Oracle docs:

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

### 2. Connect to the VM

SSH into the VM from your computer:

```bash
ssh ubuntu@YOUR_PUBLIC_IP
```

### 3. Upload this project to the VM

From your computer, copy the project folder to the VM.

Example:

```bash
scp -r /path/to/your/project ubuntu@YOUR_PUBLIC_IP:~/amazon-job-monitor
```

### 4. Create the cloud `.env` file

On the VM:

```bash
cd ~/amazon-job-monitor
cp .env.example .env
nano .env
```

Then add your real Twilio values.

The sample `.env.example` sets:

```env
CHECK_INTERVAL_SECONDS="30"
```

That is a safer starting point for a cloud VM. If you still want the original behavior, change it to:

```env
CHECK_INTERVAL_SECONDS="1"
```

### 5. Run the Oracle setup script

Still on the VM, run:

```bash
bash oracle_vm_setup.sh
```

This script will:

- install Python tools
- create the virtual environment
- install your Python packages
- create a `systemd` service
- start the monitor automatically

### 6. Check that the service is running

```bash
sudo systemctl status amazon-job-monitor
```

To watch the live logs:

```bash
sudo journalctl -u amazon-job-monitor -f
```

### 7. It will start automatically after reboots

Once the Oracle setup script finishes, the service is enabled at boot.

That means:

- your Mac can be off
- the Oracle VM keeps checking Amazon
- WhatsApp and phone-call alerts still work from the VM

## What the script does

1. It checks Amazon every `CHECK_INTERVAL_SECONDS` seconds.
2. It looks for warehouse-style jobs that mention Liverpool, NY or East Syracuse, NY.
3. On the first successful run, it saves the current jobs as a starting baseline.
4. Later, if a brand-new job appears, it:
   - prints the job information
   - sends a WhatsApp message
   - places an automated phone call
5. If nothing new appears, it prints:

`No new jobs found`

## Stop the script

Press:

```bash
Ctrl + C
```

## If alerts do not work

Check these common issues:

- your values in `.env` are missing or incorrect
- your phone has not joined the Twilio WhatsApp sandbox yet
- your Twilio number does not support voice
- your phone number format is wrong
- Twilio account restrictions are blocking the message or call

## Change the settings later

If you want to change the watched locations later, edit `TARGET_LOCATIONS` near the top of `main.py`.

Right now it is set to:

- `("Liverpool", "NY")`
- `("East Syracuse", "NY")`

You can change the timing in either of these places:

- `CHECK_INTERVAL_SECONDS` in `.env`
- `DEFAULT_CHECK_INTERVAL_SECONDS` in `main.py`

For GitHub Actions scheduling, edit:

- the cron line in `.github/workflows/amazon-job-monitor.yml`

If you only want one alert type later, edit:

- `SEND_WHATSAPP_ALERTS`
- `SEND_CALL_ALERTS`
