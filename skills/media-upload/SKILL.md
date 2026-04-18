# SKILL: Media Upload

> Image and video asset management across Google Ads and Meta platforms.

---

## Image Specifications

### Google Ads
| Placement | Size | Ratio | Max Size |
|-----------|------|-------|----------|
| Responsive Display | 1200x628 | 1.91:1 | 5MB |
| Square Display | 1200x1200 | 1:1 | 5MB |
| Logo | 1200x1200 | 1:1 | 5MB |
| Logo landscape | 1200x300 | 4:1 | 5MB |
| Formats | JPG, PNG, GIF (static) | | |

### Meta Ads
| Placement | Size | Ratio | Max Size |
|-----------|------|-------|----------|
| Feed | 1080x1080 | 1:1 | 30MB |
| Feed landscape | 1200x628 | 1.91:1 | 30MB |
| Stories/Reels | 1080x1920 | 9:16 | 30MB |
| Carousel card | 1080x1080 | 1:1 | 30MB |
| Formats | JPG, PNG | | |

## Video Specifications

### Google Ads (YouTube)
- Videos must be uploaded to YouTube first
- Reference by YouTube video ID in ad creation
- Recommended: 15-30 seconds for in-stream, 6 seconds for bumper

### Meta Ads
- Upload directly via AdVideo endpoint
- Formats: MP4, MOV
- Max size: 4GB
- Duration: 1 second to 241 minutes
- Recommended: 15-30 seconds for feed, 15 seconds for stories

## Upload Procedures

### Google Ads Image Upload
```python
from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("google-ads.yaml")
asset_service = client.get_service("AssetService")
asset_operation = client.get_type("AssetOperation")

asset = asset_operation.create
asset.name = "SunBiz MCA Ad Image"
asset.type_ = client.enums.AssetTypeEnum.IMAGE
asset.image_asset.data = open("image.jpg", "rb").read()

response = asset_service.mutate_assets(
    customer_id=customer_id,
    operations=[asset_operation]
)
```

### Meta Ads Image Upload
```python
from facebook_business.adobjects.adimage import AdImage

image = AdImage(parent_id='act_XXXXXXXXX')
image[AdImage.Field.filename] = '/path/to/image.jpg'
image.remote_create()
image_hash = image[AdImage.Field.hash]
# Use image_hash when creating AdCreative
```

### Meta Ads Video Upload
```python
from facebook_business.adobjects.advideo import AdVideo

video = AdVideo(parent_id='act_XXXXXXXXX')
video[AdVideo.Field.filepath] = '/path/to/video.mp4'
video.remote_create()
video_id = video['id']
# Use video_id when creating AdCreative
```

## Best Practices
1. Always provide multiple sizes (1:1 AND 1.91:1) for maximum placement coverage
2. Include brand logo in images (bottom-left or bottom-right corner)
3. Keep text on images to <20% of total area (especially for Meta)
4. Use high-contrast colors for CTAs
5. Test images with people vs. without people (people usually win)
6. For MCA ads: Use professional, analytical imagery (charts, infographics — no flashy/scammy visuals)
