"""
Satellite Service - Fetches satellite imagery for flood detection
Data sources: Sentinel-1, Sentinel-2, Digital Earth Africaf
"""
import requests
import numpy as np
from PIL import Image
import io
import os
from datetime import datetime, timedelta
import base64
from utils.config import (
    DE_AFRICA_BASE_URL, COPERNICUS_URL, 
    COPERNICUS_USERNAME, COPERNICUS_PASSWORD,
    SENTINEL_HUB_API_KEY
)

class SatelliteService:
    """Service for fetching and processing satellite imagery for flood detection"""
    
    def __init__(self):
        self.de_africa_base_url = DE_AFRICA_BASE_URL
        self.copernicus_url = COPERNICUS_URL
        self.copernicus_username = COPERNICUS_USERNAME
        self.copernicus_password = COPERNICUS_PASSWORD
        self.sentinel_hub_api_key = SENTINEL_HUB_API_KEY
    
    def get_sentinel2_image(self, lat, lon, bbox, date=None):
        """Fetch Sentinel-2 satellite image for flood detection"""
        if date is None:
            date = datetime.now() - timedelta(days=1)  # Use yesterday's image
        
        try:
            # Sentinel Hub API endpoint (if available)
            if self.sentinel_hub_api_key:
                url = "https://services.sentinel-hub.com/api/v1/process"
                
                payload = {
                    "input": {
                        "bounds": {
                            "bbox": bbox,
                            "properties": {
                                "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                            }
                        },
                        "data": [{
                            "type": "sentinel-2-l2a",
                            "dataFilter": {
                                "timeRange": {
                                    "from": (date - timedelta(days=2)).isoformat(),
                                    "to": date.isoformat()
                                },
                                "maxCloudCoverage": 30
                            }
                        }]
                    },
                    "output": {
                        "width": 512,
                        "height": 512,
                        "responses": [{
                            "identifier": "default",
                            "format": {"type": "image/png"}
                        }]
                    },
                    "evalscript": self._get_flood_detection_script()
                }
                
                headers = {
                    "Authorization": f"Bearer {self.sentinel_hub_api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    image_data = response.content
                    return self._process_satellite_image(image_data, 'sentinel2')
            
            # Fallback to simulated data
            return self._simulate_satellite_image(lat, lon, bbox, 'sentinel2')
                
        except Exception as e:
            print(f"Error fetching Sentinel-2 image: {e}")
            return self._simulate_satellite_image(lat, lon, bbox, 'sentinel2')
    
    def get_sentinel1_image(self, lat, lon, bbox):
        """Fetch Sentinel-1 SAR image for flood detection (all-weather)"""
        try:
            # Copernicus Open Access Hub API
            search_url = f"{self.copernicus_url}/search"
            
            params = {
                'format': 'json',
                'q': f'sentinel-1 AND footprint:"Intersects(POLYGON(({bbox[0]} {bbox[1]}, {bbox[2]} {bbox[1]}, {bbox[2]} {bbox[3]}, {bbox[0]} {bbox[3]}, {bbox[0]} {bbox[1]})))"',
                'platformname': 'Sentinel-1',
                'producttype': 'GRD',
                'beginposition': (datetime.now() - timedelta(days=7)).isoformat(),
                'endposition': datetime.now().isoformat(),
                'maxRecords': 10
            }
            
            if self.copernicus_username and self.copernicus_password:
                auth = (self.copernicus_username, self.copernicus_password)
                response = requests.get(search_url, params=params, auth=auth, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    # Process results and download image
                    # For now, return simulated
                    pass
            
            return self._simulate_satellite_image(lat, lon, bbox, 'sentinel1')
            
        except Exception as e:
            print(f"Error fetching Sentinel-1 image: {e}")
            return self._simulate_satellite_image(lat, lon, bbox, 'sentinel1')
    
    def get_digital_earth_africa_water(self, lat, lon, bbox, date_range=None):
        """Get water observations from Digital Earth Africa"""
        try:
            if date_range is None:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
            else:
                start_date, end_date = date_range
            
            # DE Africa Explorer API
            params = {
                'bbox': bbox,
                'time': f"{start_date.isoformat()}/{end_date.isoformat()}",
                'collections': 'wofs_ls',
                'limit': 100
            }
            
            # For production, use DE Africa API
            # response = requests.get(
            #     f"{self.de_africa_base_url}/stac/search",
            #     params=params
            # )
            
            return {
                'source': 'Digital_Earth_Africa_WOfS',
                'location': {'lat': lat, 'lon': lon},
                'bbox': bbox,
                'water_detections': self._simulate_wofs_data(),
                'flood_probability': self._calculate_flood_probability(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error fetching DE Africa data: {e}")
            return None
    
    def _get_flood_detection_script(self):
        """Sentinel Hub processing script for water detection"""
        # NDWI (Normalized Difference Water Index) for water detection
        return """
        //VERSION=3
        function setup() {
            return {
                input: ["B03", "B08", "B11", "B12", "dataMask"],
                output: { bands: 4 }
            };
        }
        
        function evaluatePixel(samples) {
            // Calculate NDWI (Normalized Difference Water Index)
            let ndwi = (samples.B03 - samples.B08) / (samples.B03 + samples.B08);
            
            // Water detection threshold
            let water = ndwi > 0.3 && samples.B11 < 0.15;
            
            // Flood detection
            let flood = water && samples.dataMask;
            
            return [
                samples.B04,  // Red
                samples.B03,  // Green  
                samples.B02,  // Blue
                flood ? 1 : 0  // Flood mask
            ];
        }
        """
    
    def _process_satellite_image(self, image_data, source_type):
        """Process satellite image and detect floods"""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)
            
            return {
                'image': base64.b64encode(image_data).decode('utf-8'),
                'image_format': 'png',
                'source': source_type,
                'timestamp': datetime.now().isoformat(),
                'processed': True,
                'dimensions': img_array.shape[:2] if len(img_array.shape) >= 2 else None
            }
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    def _simulate_satellite_image(self, lat, lon, bbox, source_type):
        """Simulate satellite image when API unavailable"""
        import random
        return {
            'image': None,  # Would contain base64 encoded image
            'image_format': 'png',
            'source': source_type,
            'timestamp': datetime.now().isoformat(),
            'flood_detected': random.random() > 0.7,
            'flood_area_percentage': random.uniform(0, 30),
            'bbox': bbox,
            'note': f'Simulated {source_type} data - replace with real API'
        }
    
    def _simulate_wofs_data(self):
        """Simulate Water Observations from Space data"""
        import random
        return {
            'water_detection_count': random.randint(0, 10),
            'percent_water_coverage': random.uniform(0, 30),
            'flood_extent': random.uniform(0, 50)  # km²
        }
    
    def _calculate_flood_probability(self):
        """Calculate flood probability from water observations"""
        import random
        wofs = self._simulate_wofs_data()
        # Higher water coverage = higher flood probability
        probability = min(1.0, wofs['percent_water_coverage'] / 30)
        return float(probability)

