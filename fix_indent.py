# -*- coding: utf-8 -*-
import os

def fix_indentation(fname):
    with open(fname, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    for line in lines:
        if line.startswith('                  current_vol = 50'):
            out_lines.append(line.replace('                  current_vol = 50', '                current_vol = 50'))
        elif line.startswith('                  if PYCAW_AVAILABLE:'):
            out_lines.append(line.replace('                  if PYCAW_AVAILABLE:', '                if PYCAW_AVAILABLE:'))
        elif line.startswith('                      try:'):
            out_lines.append(line.replace('                      try:', '                    try:'))
        elif line.startswith('                          _devs = AudioUtilities.GetSpeakers()'):
            out_lines.append(line.replace('                          _devs = AudioUtilities.GetSpeakers()', '                        _devs = AudioUtilities.GetSpeakers()'))
        elif line.startswith('                          _vol_intf = _devs.EndpointVolume'):
            out_lines.append(line.replace('                          _vol_intf = _devs.EndpointVolume', '                        _vol_intf = _devs.EndpointVolume'))
        elif line.startswith('                          current_vol = int(_vol_intf.GetMasterVolumeLevelScalar() * 100)'):
            out_lines.append(line.replace('                          current_vol = int(_vol_intf.GetMasterVolumeLevelScalar() * 100)', '                        current_vol = int(_vol_intf.GetMasterVolumeLevelScalar() * 100)'))
        elif line.startswith('                      except:'):
            out_lines.append(line.replace('                      except:', '                    except:'))
        elif line.startswith('                          pass'):
            out_lines.append(line.replace('                          pass', '                        pass'))
        elif line.startswith('                  status_payload = json.dumps({'):
            out_lines.append(line.replace('                  status_payload = json.dumps({', '                status_payload = json.dumps({'))
        elif line.startswith("                      'volume': current_vol,"):
            out_lines.append(line.replace("                      'volume': current_vol,", "                    'volume': current_vol,"))
        else:
            out_lines.append(line)
            
    with open(fname, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

fix_indentation('auto_shutdown.py')
print("Fixed indentation.")
