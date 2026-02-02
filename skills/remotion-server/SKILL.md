---
name: remotion-server
description: Headless video rendering with Remotion. Works on any Linux server - no Mac or GUI needed.
homepage: https://remotion.dev
metadata: {"clawdbot":{"emoji":"🎬"}}
---

# Remotion Server

Render videos headlessly on any Linux server using Remotion. No Mac or GUI required.

## Quick Start

### Create a video with text and audio:

```bash
# Navigate to the project directory
cd /home/node/clawd/remotion-projects
npm create remotion@latest my-video
cd my-video
```

### Edit the Remotion composition to include:

```tsx
import {Composition} from 'remotion';
import {Audio} from 'remotion';
import {Subtitles} from '@remotion/subtitles';

export const MyVideo: React.FC = () => {
  return (
    <Composition>
      <Audio src="/path/to/audio.mp3" />
      <Subtitles src="/path/to/subtitles.srt" />
      {/* Your video content */}
    </Composition>
  );
};
```

### Render:

```bash
npx remotion render MyVideoComposition out/video.mp4
```

## Using with TTS

1. Generate audio using `tts` tool:
   ```javascript
   tts("Your script text here")
   // Returns: MEDIA: /tmp/tts-xxx/voice-xxx.mp3
   ```

2. Save the MEDIA path

3. Use in Remotion composition

## Simple Video Creation Script

For news videos, use this workflow:

1. Generate script → saved to `script.txt`
2. Generate TTS audio → get MEDIA: path
3. Create SRT subtitles → `subtitles.srt`
4. Render with Remotion

## Installation

```bash
cd /home/node/clawd/skills/remotion-server
bash scripts/setup.sh
```

## Linux Dependencies

```bash
sudo apt-get install -y \
  libnss3 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libgbm1 libpango-1.0-0 \
  libcairo2 libxcomposite1 libxdamage1 \
  libxfixes3 libxrandr2
```
