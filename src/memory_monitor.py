"""
Memory monitoring module for tracking RAM usage in real-time.
"""

import psutil
import os

class MemoryMonitor:
    """Monitor system and application memory usage."""
    
    def __init__(self, audio_engine=None):
        self.audio_engine = audio_engine
        try:
            self.process = psutil.Process(os.getpid())
            self.psutil_available = True
        except:
            self.psutil_available = False
        self.buffer_memory_estimate = 0
        
    def is_available(self):
        """Check if memory monitoring is available."""
        return self.psutil_available
    
    def update_buffer_estimate(self, engine):
        """Calculate estimated memory usage of audio buffers."""
        if not engine:
            return 0
            
        buffer_size_seconds = 300
        sample_rate = 44100
        channels = 2
        bytes_per_sample = 4
        num_buffers = 4
        
        if hasattr(engine, 'next_ambient_buffer') and hasattr(engine, 'next_rhythm_buffer'):
            if engine.next_ambient_buffer is not None and engine.next_rhythm_buffer is not None:
                num_buffers = 4
            else:
                num_buffers = 2
        
        estimated_bytes = (
            buffer_size_seconds * 
            sample_rate * 
            channels * 
            bytes_per_sample * 
            num_buffers
        )
        
        self.buffer_memory_estimate = estimated_bytes / (1024 * 1024)
        return self.buffer_memory_estimate
    
    def get_system_memory(self):
        """Get system-wide memory usage."""
        if not self.psutil_available:
            return {'percent': 0, 'available': 0, 'total': 0, 'used': 0}
        
        try:
            system = psutil.virtual_memory()
            return {
                'total': system.total / (1024 * 1024 * 1024),
                'available': system.available / (1024 * 1024 * 1024),
                'used': system.used / (1024 * 1024 * 1024),
                'percent': system.percent
            }
        except:
            return {'percent': 0, 'available': 0, 'total': 0, 'used': 0}
    
    def get_application_memory(self):
        """Get this application's memory usage."""
        if not self.psutil_available:
            return {'rss': 0, 'vms': 0}
        
        try:
            mem_info = self.process.memory_info()
            return {
                'rss': mem_info.rss / (1024 * 1024),
                'vms': mem_info.vms / (1024 * 1024),
            }
        except:
            return {'rss': 0, 'vms': 0}
    
    def get_memory_status(self):
        """Get comprehensive memory status."""
        system = self.get_system_memory()
        app = self.get_application_memory()
        
        if self.audio_engine and self.psutil_available:
            self.update_buffer_estimate(self.audio_engine)
        buffer_estimate = self.buffer_memory_estimate
        
        total_app_estimate = app['rss'] + buffer_estimate
        
        pressure = "LOW"
        if system['percent'] > 80:
            pressure = "CRITICAL"
        elif system['percent'] > 65:
            pressure = "HIGH"
        elif system['percent'] > 50:
            pressure = "MODERATE"
        
        return {
            'system_percent': system['percent'],
            'system_available_gb': system['available'],
            'system_total_gb': system['total'],
            'app_rss_mb': app['rss'],
            'app_vms_mb': app['vms'],
            'buffers_mb': buffer_estimate,
            'total_estimated_mb': total_app_estimate,
            'pressure_level': pressure,
            'available': self.psutil_available
        }
    
    def get_memory_summary(self):
        """Get a short summary string for display."""
        if not self.psutil_available:
            return "RAM: [--]"
        
        status = self.get_memory_status()
        percent = status['system_percent']
        
        # Simple progress bar
        width = 15
        filled = int((percent / 100) * width)
        bar = '█' * filled + '░' * (width - filled)
        
        if percent >= 80:
            indicator = "🔴"  # Red circle
        elif percent >= 65:
            indicator = "🟡"  # Yellow circle
        else:
            indicator = "🟢"  # Green circle
        
        return f"{indicator} RAM: [{bar}] {percent:.0f}% ({status['app_rss_mb']:.0f}MB)"
