# NAI Auto Generator V4.5 User Manual

**Version:** V4.5_2.6.01.09  
**Last Updated:** January 2026

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Basic Features](#basic-features)
   - [Login](#login)
   - [Prompt Input](#prompt-input)
   - [Image Generation](#image-generation)
   - [Saving and Loading Settings](#saving-and-loading-settings)
   - [Options Settings](#options-settings)
3. [Key Features](#key-features)
   - [Character Prompts (V4)](#character-prompts-v4)
   - [Character Reference](#character-reference)
   - [Image to Image (img2img)](#image-to-image-img2img)
   - [Image Enhancement](#image-enhancement)
   - [Image Inpainting](#image-inpainting)
   - [Vibe Transfer](#vibe-transfer)
4. [Advanced Settings](#advanced-settings)
5. [Wildcard System](#wildcard-system)
6. [Auto Generation](#auto-generation)
7. [Shortcuts and Tips](#shortcuts-and-tips)

---

## Overview

NAI Auto Generator V4.5 is a powerful desktop application that utilizes NovelAI's image generation API. 
It provides advanced features not available in the NovelAI web interface, enabling more efficient and sophisticated AI image generation.

### Key Features

- **Full V4 Model Support**: Complete support for NovelAI's latest model, NovelAI Diffusion V4.5 Full
- **Advanced Character Control**: Precise character generation through Character Prompts and Character Reference
- **Image Editing Features**: Image modification and enhancement via img2img, Enhancement, and Inpainting
- **Automation**: Workflow optimization with wildcards, batch generation, and auto-generation
- **Multi-language Support**: Korean, English, Japanese, and Chinese interface

---

## Basic Features

This section guides you through the basic features for using NAI Auto Generator.

### Login

Log in with your NovelAI account to activate image generation features.

#### How to Login

1. **Login from Menu**
   - Select `Files` → `Log in`

2. **Enter Account Information**
   - Username: NovelAI account email or username
   - Password: NovelAI account password
   - If you created an ID with Google ID linking, change (set) your password in User Settings → Account on the Web before use

3. **Auto Login** (Optional)
   - Check the `Auto login next time` checkbox
   - Auto login on next launch

4. **Verify Login**
   - "Login Complete" message displays in the top status bar
   - ANLAS balance displayed

#### Important Notes

- Username and password are sent only to NovelAI servers
- They are not sent to this app's servers
- When auto login is enabled, credentials are stored encrypted locally

---

### Prompt Input

Enter prompts and negative prompts for image generation.

#### Prompt

Describe the content of the image you want to generate.

**Basic Format**:
```
1girl, blue eyes, long hair, standing, outdoor, smile
```

**Recommended Structure**:
```
[Subject], [Appearance], [Pose/Action], [Background], [Mood/Emotion], [Quality Tags]
```

**Example**:
```
1girl, blue dress, long blonde hair, standing in garden, 
happy smile, sunlight, masterpiece, best quality, high quality
```

#### Negative Prompt

Specify elements you want to exclude from generation.

**Common Negative Prompts**:
```
lowres, bad quality, worst quality, bad anatomy, 
missing fingers, extra digits, blurry, text, watermark
```

#### Advanced Prompt Syntax

##### 1. Emphasis (Weighting)

**Using Curly Braces**:
- `{tag}`: 1.05× emphasis
- `{{tag}}`: 1.1025× emphasis (nestable)
- `{{{tag}}}`: 1.157625× emphasis

**Using Square Brackets**:
- `[tag]`: 0.95× de-emphasis
- `[[tag]]`: 0.9025× de-emphasis (nestable)

**Exact Value Specification** (Colon Emphasis):
```
1.2::masterpiece ::
0.8::simple background ::
-2::multiple views ::
```
- Format: `weight::text ::`
- Weight range: typically 0.5 ~ 1.5
- Negative weights: Use when you want to exclude elements (not recommended for negative prompts)

##### 2. Artist Tags

Apply the style of a specific artist.
```
{artist: artist_name}
```

Example:
```
1girl, {artist:abcd}, fantasy art style
```

##### 3. Year Tags

Reference the style of a specific year.
```
year 2024, year 2025
```

##### 4. Quality Tag Combinations

```
masterpiece, best quality, high quality, amazing quality, 
very aesthetic, intricate details, detailed shading
```

#### Syntax Highlighting

Syntax is automatically highlighted when entering prompts:
- **Curly braces**: Displayed in orange
- **Square brackets**: Displayed in blue
- **Colon Emphasis**: Numbers and separators shown in different colors
- **Artist tags**: Highlighted in unique color

---

### Image Generation

Guide to basic image generation methods.

#### Image Options

##### Size (Resolution)

Select desired resolution from dropdown menu:

**Normal Resolutions**:
- 1024×1024 (Square)
- 832×1216 (Portrait)
- 1216×832 (Landscape)

**Large Resolutions**:
- 1472×1472 (Square)
- 1024×1536 (Portrait)
- 1536×1024 (Landscape)

**Note**:
- For Opus tier, normal resolutions don't consume ANLAS
- Large resolutions consume ANLAS
- Image Enhancement only supports Normal resolutions

##### Width / Height

You can directly input resolution values.
- Range: 64 ~ 2048 pixels
- Recommended to use multiples of 64

##### Random

When checkbox is enabled, a random resolution is selected for each generation.

##### Sampler

Select the image generation algorithm.

**Main Samplers**:
- **k_euler_ancestral**: Default, diverse results
- **k_euler**: Consistent results
- **ddim**: Fine control
- **k_dpmpp_2s_ancestral**: High quality, takes some time
- **k_dpmpp_sde**: Very high quality, takes more time

##### Steps

Number of iterations in the generation process.
- Default: 28
- Range: 1~50
- Higher values: More precise but takes longer
- Recommended: 28 (default) ~ 40 (high quality)

##### Seed

Random number value that makes generation results reproducible.
- **Random**: Uses different seed each time (diverse results)
- **Fix**: Uses fixed seed (reproduces identical results)
- Range: 0 ~ 4,294,967,295

**Usage**:
- Fix the seed of a result you like to generate similar images
- Slightly modify only the prompt to create variations

---

### Saving and Loading Settings

You can save and load current prompts and parameter settings.

#### Saving Settings

1. **Use Menu**
   - `Files` → `Save Settings` (Shortcut: Ctrl+S)
   
2. **Enter Filename**
   - Save as .txt file with desired name
   
3. **Saved Contents**
   - Prompt
   - Negative Prompt
   - Character Prompts
   - All generation parameters (resolution, sampler, steps, etc.)
   - Character Reference settings
   - Image to Image settings

#### Loading Settings

1. **Use Menu**
   - `Files` → `Load Settings` (Shortcut: Ctrl+O)
   
2. **Select File**
   - Choose saved .txt settings file
   
3. **Verify Application**
   - Prompt and all parameters are restored

#### Loading Settings from Images

PNG images generated with NovelAI contain metadata that allows settings restoration.

1. **Drag and Drop**
   - Drop PNG or WEBP image onto main screen
   
2. **Use Menu**
   - `Files` → `Open file`
   - Select PNG or WEBP image

3. **Restored Contents**
   - Prompt and all generation parameters
   - Character Prompts (if present)
   - Result image preview

---

### Options Settings

Manage global application settings.

#### Opening Options Dialog

- Select `Files` → `Option` menu

#### Folder Path Settings

Specify default folder locations for each feature.

##### Results Save Folder

Location where generated images are saved.
- **Default Path**: `UserFolder/NAI-Auto-Generator/results`
- **How to Change**: Select desired folder with browse button
- **Purpose**: All generated images saved to this folder

##### Settings File Save Folder

Location where settings files (.txt) are saved.
- **Default Path**: `UserFolder/NAI-Auto-Generator/settings`
- **Purpose**: Location of files saved with Save Settings

##### Wildcard Files Folder

Folder where wildcard text files are located.
- **Default Path**: `UserFolder/NAI-Auto-Generator/wildcards`
- **Purpose**: Wildcard files used in `##filename##` format

##### Tag Completion File Path

Path to CSV file used for tag auto-completion.
- **Default File**: `tag_completion.csv`
- **Purpose**: Auto-completion suggestions when entering prompts
- **When Changed**: Recommend refreshing tags

#### Log Settings

Log recording settings for troubleshooting.

##### Enable Debug Mode

Checkbox to turn debug mode on or off.
- **Disabled** (Default): Only basic information recorded
- **Enabled**: Detailed debug information recorded
  - Function call tracking
  - Variable value recording
  - Detailed error information

**When to Use**:
- When problems occur
- When reporting bugs to developers

##### Log Detail Level

Controls the amount of information recorded in logs.
- **NORMAL**: Only general task information
- **DETAILED**: More detailed information

##### Log File Location

Specifies folder where log files are saved.
- **Default Path**: `UserFolder/NAI-Auto-Generator/logs`
- **Filename Format**: `nai_generator_YYYYMMDD.log`
- **Open Log Folder Button**: Opens log file location in explorer

#### Continuous Generation Settings

Customize the count for Quick Generation buttons.

##### Quick Generation Count

Set count for 4 preset buttons in auto-generation dialog.
- **Button 1**: Default 5 images (changeable: 1~9999)
- **Button 2**: Default 10 images
- **Button 3**: Default 50 images
- **Button 4**: Default 100 images

**Usage**:
- Customize to frequently used counts
- Example: Set to 5, 20, 100, 500

#### Prompt Settings

Configure prompt input related features.

##### Syntax Highlighting

Highlights syntax with colors when entering prompts.
- Visually distinguishes curly braces, square brackets, Colon Emphasis, etc.
- Prevents syntax errors when writing prompts

#### Font Settings

##### Font Size

Adjust font size of prompt input field.
- Range: 8 ~ 32pt
- Default: 18pt
- Adjustable for readability

#### Tag Settings

##### Refresh Tags

Reload tag auto-completion list.
- **When to Use**: 
  - After modifying tag CSV file
  - After adding new tag files
- **How**: 
  - Click "Refresh Tags" button in Options
  - Or `Files` → `Reload Tag Completion` menu

**Note**: Can update tag list without restarting application

#### Theme Settings

Change application UI theme.
- **Default Theme**: Follow system settings
- **Light Theme**: Use light background
- **Dark Theme**: Use dark background (dark mode)

**Application**:
- Changes immediately reflected in UI after theme selection
- No restart required

#### Filename Format Settings

Customize filename format for generated images.

##### Supported Placeholders

- `[datetime]`: Date and time (e.g., 20250118_143052)
- `[date]`: Date only (e.g., 20250118)
- `[time]`: Time only (e.g., 143052)
- `[prompt]`: Prompt text
- `[character]`: Character prompt
- `[seed]`: Seed value

##### Word Count Limit

You can limit the word count of prompt and character prompt.
- Addresses Windows filename length limit (260 characters)
- Prevents excessively long filenames

##### Format Examples

- `[datetime]_[prompt]` (Default)
- `[date]_[seed]_[prompt]`
- `[character]_[datetime]`
- `[prompt]_[time]_s[seed]`

**Benefits**:
- Easy file organization and search
- Prevents excessively long filename errors
- Manage files in your preferred way

---

## Key Features

### Character Prompts (V4)

Feature introduced in V4 model that allows specifying multiple characters individually in an image and controlling their positions.

#### Basic Usage

1. **Enable from Menu**
   - Select `View` → `Character Prompts` (or `F1` shortcut)
   
2. **Add Character**
   - Click `+ Add Character` button
   - Separate prompt input available for each character
   
3. **Select Position Method**
   - **By Coordinates**: Specify exact position with X, Y values
   - **By Region**: Select position by dividing screen into regions
   
4. **Enter Character Prompt**
   - Describe each character's appearance
   - Example: "1girl, blue dress, long hair"
   
5. **Generate**
   - Click main generate button
   - Characters generated at specified positions

#### Coordinate System

**By Coordinates**:
- Range: 0.0 ~ 1.0 (relative position)
- (0.0, 0.0) = Top left
- (1.0, 1.0) = Bottom right
- (0.5, 0.5) = Center

**By Region**:
- Screen divided into 9 regions (3×3 grid)
- Simply select region (Top-Left, Center, Bottom-Right, etc.)

#### Tips

- **Multiple Characters**: Can add up to 6 characters
- **Character Interaction**: Characters automatically interact naturally when positioned close
- **Background Prompt**: Main prompt used for overall atmosphere and background
- **Character Priority**: Characters added first have higher priority

#### Notes

- Character Prompts are V4 model exclusive feature
- Automatic switching to V4.5 model when enabled
- Cannot be used with Character Reference

---

### Character Reference

Feature that maintains character consistency by using a reference photo to generate the same character in different poses and situations.

#### Basic Usage

1. **Enable Feature**
   - Select `View` → `Character Reference` (or `F1` shortcut)
   
2. **Select Reference Image**
   - Click `Select Image` in Reference Image widget
   - Or drag and drop image
   
3. **Set Parameters**
   - **Fidelity (Character Consistency)**: 0.0 ~ 1.0
     - Controls how closely generated character matches reference
     - Higher values = more similar to reference
     - Recommended: 0.8 or higher
   
   - **Style Aware**: Checkbox
     - When checked: Apply both character appearance and art style
     - When unchecked: Apply only character appearance
   
4. **Add Description** (Optional)
   - Enter text describing the reference image
   - Example: "girl with blue eyes and long hair"
   - Helps AI better understand the character

5. **Enter Prompt and Generate**
   - Describe desired pose, background, situation in prompt
   - Reference character maintains consistency across different scenes

#### Information Extracted

After selecting reference image, automatically extracts:
- **Character Features**: Hair color, eye color, clothing, accessories
- **Style Information**: Art style, line drawing style, coloring method (only when Style Aware enabled)

#### Parameters Explained

**Fidelity**:
- 0.0~0.4: Loose interpretation, large variations
- 0.5~0.7: Moderate similarity, some flexibility
- 0.8~1.0: High similarity, close to reference (Recommended)

**Style Aware**:
- Enabled: Applies both character AND art style
- Disabled: Applies only character appearance

#### Tips

- **High Quality Reference**: Use clear, high-resolution reference images
- **Single Character**: Reference images with only one character work best
- **Consistent Poses**: Fix seed to maintain character consistency across generations
- **Style Separation**: Disable Style Aware to separate character and art style

#### Notes

- Character Reference exclusive to V4.5 model
- Cannot be used simultaneously with Vibe Transfer
- Requires Director Tools parameters instead of standard reference system
- Automatically switches to V4.5 model when enabled

---

### Image to Image (img2img)

Feature that modifies existing images or generates new images based on them.

#### Basic Usage

1. **Enable Feature**
   - Select `View` → `Image to Image` (or `F2` shortcut)
   
2. **Select Base Image**
   - Click `Select Image` in Image to Image widget
   - Or drag and drop image
   
3. **Adjust Parameters**
   - **Strength (Modification Degree)**: 0.01 ~ 0.99
     - Higher values = more different from original
     - Lower values = closer to original
     - Recommended: 0.4~0.7
   
   - **Noise (Randomness)**: 0.00 ~ 0.99
     - Randomness in generation process
     - Generally recommend keeping at 0.00

4. **Enter Prompt**
   - Describe desired changes or additional elements
   - Example: "change dress color to red"
   
5. **Generate**
   - Modified/new image generated based on original

#### Strength Guide

- **0.1~0.3**: Minimal changes, detail refinement
- **0.4~0.6**: Moderate changes, partial modifications
- **0.7~0.9**: Major changes, almost new image

#### Use Cases

- **Color Changes**: Modify clothing, background colors
- **Pose Adjustments**: Slightly change character poses
- **Detail Enhancement**: Add or refine details
- **Style Changes**: Change art style while maintaining composition
- **Element Addition**: Add new elements to image

#### Tips

- **Strength Control**: Start with low value and gradually increase
- **Seed Fixation**: Fix seed to get similar results
- **Resolution Match**: Using same resolution as original works best
- **Prompt Clarity**: Use clear, specific descriptions

---

### Image Enhancement

Feature that upscales images and enhances details.

#### Basic Usage

1. **Enable Feature**
   - Select `View` → `Image Enhancement` (or `F3` shortcut)
   
2. **Select Image**
   - **Select Image**: Choose single image for enhancement
   - **Select Folder**: Process multiple images at once (batch Enhancement)

3. **Select Upscale Ratio**
   - **1x**: Maintain original size (enhance details only)
   - **1.5x**: Increase resolution by 1.5×

4. **Adjust Parameters**
   - **Strength**: 0.01 ~ 0.99 (Default: 0.40)
     - Controls detail enhancement strength
     - Too high may differ from original
   
   - **Noise**: 0.00 ~ 0.99 (Default: 0.00)
     - Randomness in generation process
     - Generally recommend keeping at 0.00

5. **Execute Generation**
   - Click `Start Enhance` button
   - Batch mode processes sequentially automatically

#### Resolution Mapping (1.5x)

| Original Resolution | Enhanced Resolution |
|------------|-------------------|
| 1024×1024 | 1536×1536 |
| 832×1216 | 1280×1856 |
| 1216×832 | 1856×1280 |

#### Batch Enhancement

1. Select image folder with `Select Folder` button
2. Automatically detects images with NovelAI metadata
3. Start batch processing with `Start Enhance` button
4. 3-second wait between each image (prevents API limits)
5. Real-time progress display

#### Tips

- **High Quality Output**: Safely enhance details with Strength 0.3~0.5
- **Batch Processing**: Useful when upscaling multiple images at once
- **Metadata Required**: Enhancement requires original image's NovelAI metadata

#### Supported Resolutions

- **Normal resolutions only supported**: 1024×1024, 832×1216, 1216×832
- **Large resolutions not supported**: 1472×1472, 1024×1536, 1536×1024
- Warning message displayed when selecting Large resolution images

#### Cost

- Enhancement uses **additional ANLAS** per generation (varies by upscale ratio)

---

### Image Inpainting

Feature that selectively regenerates specific areas of an image.

#### Basic Usage

1. **Load Image with Image to Image**
   - Select image to modify in img2img widget

2. **Open Mask Painting Dialog**
   - Click `Paint Mask` button

3. **Specify Mask Area**
   - Drag with mouse to paint area to regenerate
   - Painted area shown with red overlay
   - Precise work possible in 8×8 pixel grid units

4. **Adjust Brush Size**
   - Adjust 1~20 grid cells with slider (Default: 3)
   - Size 1 = 8×8 pixels
   - Size 3 = 24×24 pixels (Default)
   - Size 20 = 160×160 pixels (Maximum)

5. **Invert Mask** (Optional)
   - Enable `Invert Mask` checkbox
   - Regenerate unpainted areas

6. **Confirm and Generate**
   - Click `OK` button
   - Enter prompt on main screen and generate
   - Only masked area is regenerated

#### Use Cases

- **Partial Corrections**: Regenerate only specific parts like face, hands, background
- **Element Removal**: Mask and regenerate unwanted elements
- **Element Addition**: Mask empty area and add new elements
- **Style Unification**: Modify inconsistent parts to match rest of image

#### Mask Inversion Usage

- **Normal Mode**: Regenerate painted areas (typical use)
- **Invert Mode**: Regenerate unpainted areas (useful when modifying most of image)

#### Notes

- Mask persists even after closing dialog (previous mask shown when reopened)
- Works in 8×8 grid units for very precise work
- Green grid lines show block boundaries

---

### Vibe Transfer

Feature that applies the mood and style of a reference image to new images.

#### Basic Usage

1. **Select Reference Image**
   - Click `Select Image` in Reference Image widget
   - Or drag and drop image

2. **Adjust Parameters**
   - **Reference Strength**: 0.0 ~ 1.0
     - Controls reference image influence
     - Higher values = more similar style to reference

3. **Enter Prompt and Generate**
   - Enter desired content in prompt
   - Color scheme, mood, and style of reference image applied

#### Difference from Character Reference

| Feature | Character Reference | Vibe Transfer |
|-----|-------------------|--------------|
| Purpose | Maintain character appearance | Transfer mood/style |
| Reference Target | Specific character | Overall feeling |
| Usage | Same character, different poses | Similar mood images |
| Compatibility | Can use with Character Prompts | Cannot use simultaneously with Character Reference |

#### Tips

- **Style Consistency**: Maintain consistent feel across series of images
- **Color Control**: Transfer specific color schemes or lighting moods
- **Reference Strength**: 0.3~0.6 generally produces natural results

#### Notes

- Character Reference and Vibe Transfer cannot be used simultaneously
- Choose one of the two features

---

## Advanced Settings

### Variety+ (Increase Diversity)

Feature that skips CFG in early generation stages to create more diverse results.

- **Location**: Advanced Settings section
- **Checkbox**: Enable/disable Variety+
- **Effect**: Create more diverse variations even with same seed
- **API Parameter**: Sets `skip_cfg_above_sigma = 19`

### Noise Schedule

Advanced setting that controls how noise is applied.

- **Default**: karras
- **Options**: native, karras, exponential, polyexponential
- **Effect**: Controls noise distribution in image generation process

### Legacy Mode

Mode that uses V3 model's prompt processing method.

- **Purpose**: When V3 style results are needed
- **General Use**: Recommend keeping disabled

### Sampler

Select image generation algorithm.

- **k_euler_ancestral**: Default sampler, diverse results
- **k_euler**: Consistent results
- **ddim**: Fine control possible
- Supports various other samplers

### Steps

Number of iterations in generation process.

- **Default**: 28
- **Range**: 1~50
- **Effect**: Higher values more precise but take longer

### Prompt Guidance

Controls AI's adherence to the prompt.

- **Default**: 5.0
- **Range**: 0.0~30.0
- **Low Values**: More creative and unpredictable results
- **High Values**: More faithful to prompt

---

## Wildcard System

Wildcards are a feature for defining randomly selected text patterns in prompts.

### Basic Syntax

#### Simple Wildcard
```
##filename##
```
- Randomly selects one line from `filename.txt` file in `wildcards` folder

#### Loop Wildcard (Loopcard)
```
##filename*N##
```
- Maintains same value for N generations
- Example: `##characters*3##` - Keep same character for 3 generations

#### Nested Selection (Lessthan)
```
{option1|option2|option3}
```
- Randomly selects one from multiple options
- Example: `{red|blue|green} dress` → "red dress" or "blue dress" or "green dress"

### Creating Wildcard Files

1. **File Location**
   - Create `.txt` file in `wildcards` folder
   - Menu: `Folders` → `Wildcards Folder` (F6) to open folder

2. **File Contents**
   - One option per line
   - Empty lines ignored
   
   Example (`characters.txt`):
   ```
   1girl, blue eyes, long hair
   1boy, red hair, short hair
   1girl, green eyes, ponytail
   ```

3. **Use in Prompt**
   ```
   ##characters##, standing, outdoors
   ```
   → Generates with different character each time

### Advanced Usage

#### Maintain Continuity with Loopcard
```
##pose*5##, ##expression*5##, ##background##
```
- pose and expression maintained for 5 generations
- background changes each time

#### Conditional Selection
```
{##summer_clothes##|##winter_clothes##}
```
- Selects between summer or winter clothes wildcard

#### Use with Weighting
```
{1.2::##strong_features##::0.8|##soft_features##}
```

---

## Auto Generation

Feature that automatically generates multiple images in succession.

### Auto Generation Dialog

1. **Open**
   - Click `Generate by Settings` button
   - Or expansion button next to main generate button

2. **Quick Generation**
   - Start immediately with 5, 10, 50, 100 image buttons
   - Can customize count for each button in Options

3. **Manual Input**
   - Generation Count: Enter desired number (-1 = unlimited)
   - Generation Interval: Wait time between each generation (seconds)
   - Ignore Errors: Continue even if generation error occurs when checked

4. **Start and Stop**
   - Start with `Auto Generate` button
   - Stop with `Stop Generation` button

### Batch Settings Files

Can generate by sequentially applying multiple settings.

1. **Prepare Settings Files**
   - Prepare multiple `.txt` settings files
   - Save different prompts or parameters in each file

2. **Execute Batch Generation**
   - Select multiple files when choosing
   - Start auto generation
   - Generates sequentially with each setting

### Status Display

Progress shown in status bar during auto generation:
- "Continuous generation (5/10)"
- "Waiting for next generation... (3 seconds)"
- "Error occurred. Retrying in 5 seconds..."

---

## Shortcuts and Tips

### Main Shortcuts

#### View Menu
- `F1`: Toggle Character Reference
- `F2`: Toggle Image to Image
- `F3`: Toggle Image Enhance
- `F11`: Toggle Results Panel
- `Ctrl+R`: Reset Layout
- `Ctrl+Shift+I`: Reset Image Size

#### Folders Menu
- `F5`: Open Results Folder
- `F6`: Open Wildcards Folder
- `F7`: Open Settings Folder

#### File Menu
- `Ctrl+S`: Save Settings
- `Ctrl+O`: Load Settings

### Prompt Writing Tips

#### Effective Prompt Structure
```
[Subject], [Details], [Style], [Quality Tags]
```

Example:
```
1girl, blue eyes, long hair, standing, outdoor, 
{artist: xxx}, official art, masterpiece, best quality
```

#### Using Weights
- `{tag}`: 1.05× emphasis
- `{{tag}}`: 1.1025× emphasis (nestable)
- `[tag]`: 0.95× de-emphasis
- `1.2::tag::`: 1.2× emphasis (exact value)

#### Artist Tags
```
{artist: artist_name}
```
- Apply style of specific artist that NovelAI learned

### Efficient Workflow

#### 1. Generate Base Image
- Create desired composition with Character Prompts
- Generate multiple times to select preferred composition
- Fix seed to maintain consistent results

#### 2. Fine-tune Details
- Secure character consistency with Character Reference
- Partial modifications with Image to Image
- Regenerate problem areas only with Inpainting

#### 3. Final Polish
- Enhance resolution and strengthen details with Enhancement

#### 4. Mass Production
- Auto-generate various variations with wildcards
- Generate multiple images continuously with auto generation feature

### Troubleshooting

#### When Generation Fails
1. Check prompt length (not too long)
2. Check negative prompt
3. Verify resolution is within supported range
4. Check ANLAS balance
5. Check logs (Options → Log Level)

#### When Image Doesn't Come Out as Desired
1. Adjust Prompt Guidance value (lower or raise)
2. Try changing Sampler
3. Increase Steps (28 → 32~40)
4. Adjust wildcard patterns

#### When Character Reference Doesn't Work
1. Verify reference image has correct resolution
2. Adjust Fidelity value (recommend 0.8 or higher)
3. Check Style Aware settings
4. Verify not using simultaneously with Vibe Transfer (cannot use together)

---

## Additional Information

### Filename Format Settings

Can customize filename format for generated images in Options.

**Supported Placeholders**:
- `[datetime]`: Date and time
- `[date]`: Date only
- `[time]`: Time only
- `[prompt]`: Prompt text
- `[character]`: Character prompt
- `[seed]`: Seed value

**Examples**:
- `[datetime]_[prompt]` (Default)
- `[character]_[date]_[seed]`
- `[prompt]_[datetime]`

### Tag Auto-completion

Can use auto-completion feature when entering prompts.

- **Tag File Path**: Configurable in Options
- **Reload**: Files → Reload Tag Completion (after modifying tag file)
- **Usage**: Suggestions automatically displayed when you start typing

### Log System

Can check detailed logs for troubleshooting.

- **Log Level**: Select NORMAL or DETAILED in Options
- **Log Location**: Check and change in Options
- **Open Log Folder**: Click button in Options dialog

---

## Version Information

**Current Version**: V4.5_2.6.01.09  
**Update History**: [GitHub Releases](https://github.com/sagawa8b/NAI-Auto-Generator-V4/releases)

---

## Credits

- **Original**: [DCP-arca/NAI-Auto-Generator](https://github.com/DCP-arca/NAI-Auto-Generator)
- **V4/V4.5 Update**: sagawa8b
- **Community**: [Arca.live AI Art Board](https://arca.live/b/aiart)

---

## Disclaimer

This application is an unofficial third-party tool not developed or managed by NovelAI and is unaffiliated with NovelAI.

---

**End**
