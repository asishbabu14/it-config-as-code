# Renewing an Apple Push certificate

Apple Push certificates used by device management are issued for about a year. This lab does not talk to Apple. The inventory holds the date, and the expiry monitor nags before it passes.

The sample entry is `lab-mdm-apple-push` in `tools/expiry-monitor/inventory/lab.yaml`. Its `not_after` is a fixture date so the demo clock can show a critical row. Replace that date when you track a real certificate.

## 1. Confirm the row

```bash
python3 tools/expiry-monitor/monitor.py \
  --inventory tools/expiry-monitor/inventory/lab.yaml
```

Notice starts at 60 days, warning at 30, critical at 7. Expired is anything already past `not_after`.

## 2. Renew with Apple

On a workstation, using the device management service that holds the certificate:

1. Create a certificate signing request from that service. Reuse the same service record if it already has a push certificate. A brand new certificate, instead of a renewal of the existing one, can force devices to re-enroll.
2. Sign in to the Apple Push Certificates portal and renew the certificate that matches the topic already in use.
3. Download the renewed certificate and import it back into the device management service.
4. Confirm the service shows the new expiry and that a test device still checks in.

This repo cannot do those steps. There is no provider resource for the Apple portal here.

## 3. Update the inventory

Open a pull request that changes `not_after` on `lab-mdm-apple-push` to the new timestamp in UTC:

```yaml
- name: lab-mdm-apple-push
  kind: apple_push
  not_after: "2029-04-06T00:00:00Z"
```

Run the monitor with `--now` left unset and confirm the row is `ok`. The scheduled workflow uses the real clock and fails when the row is critical, expired, or an error, so a stale date will wake you up again.

## 4. If the certificate already expired

Devices stop checking in once the certificate lapses. Renew it, import it into the same service record, update the inventory, and then deal with devices that no longer check in. Deleting the service record and starting over is a larger outage. Avoid that unless the topic is already lost.

## Rollback

A wrong `not_after` in git is reverted by another pull request. A wrong certificate imported into the device service is rolled back by importing the previous certificate again, if you still have the file. Keep the previous file until the new one has been in use and a device has checked in.
