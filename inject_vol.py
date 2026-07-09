# -*- coding: utf-8 -*-
import os
import re

def update_payload_with_volume(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define the volume reading snippet
    volume_snippet = '''
                  current_vol = 50
                  if PYCAW_AVAILABLE:
                      try:
                          _devs = AudioUtilities.GetSpeakers()
                          _vol_intf = _devs.EndpointVolume
                          current_vol = int(_vol_intf.GetMasterVolumeLevelScalar() * 100)
                      except:
                          pass
                  '''

    # Function to replace the payload
    # Find `status_payload = json.dumps({`
    # Replace with volume_snippet + status_payload where 'volume': current_vol is added
    
    # We can do this safely by splitting around `status_payload = json.dumps({`
    parts = content.split("status_payload = json.dumps({")
    if len(parts) > 1:
        new_content = parts[0]
        for i in range(1, len(parts)):
            part = parts[i]
            # Find the first closing `})` or `}).encode`
            # Actually, just inserting `'volume': current_vol,\n` after the brace is easier
            new_part = volume_snippet + "status_payload = json.dumps({\n                      'volume': current_vol," + part
            new_content += new_part
        content = new_content

    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)

update_payload_with_volume('auto_shutdown.py')
print("Updated auto_shutdown.py with volume telemetry")
