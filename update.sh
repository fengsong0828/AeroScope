#!/bin/bash
# AeroScope 一键更新部署
cd /var/www/aeroscope
git pull
sudo systemctl restart aeroscope
echo "✓ 更新完成"
sudo systemctl status aeroscope --no-pager -l | head -5
