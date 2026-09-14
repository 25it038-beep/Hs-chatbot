/*
 * Device Manager Component
 * React component for managing voice-enabled devices
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Loader2, Trash2, Pause, Play, Plus, Edit2 } from 'lucide-react';

interface Device {
  id: string;
  name: string;
  device_type: string;
  os_type: string;
  voice_enabled: boolean;
  last_seen: string;
  status: 'active' | 'paused' | 'revoked';
  created_at: string;
}

export const DeviceManager: React.FC<{ orgId: string }> = ({ orgId }) => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [newDeviceName, setNewDeviceName] = useState('');
  const [newDeviceType, setNewDeviceType] = useState('desktop');

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/voice/devices?org_id=${orgId}`);
      if (response.ok) {
        const data = await response.json();
        setDevices(data);
      }
    } catch (error) {
      console.error('Error loading devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddDevice = async () => {
    if (!newDeviceName) return;

    try {
      const response = await fetch('/api/voice/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: orgId,
          name: newDeviceName,
          device_type: newDeviceType,
          os_type: 'windows', // TODO: Detect OS
        }),
      });

      if (response.ok) {
        const newDevice = await response.json();
        setDevices([...devices, newDevice]);
        setShowAddDialog(false);
        setNewDeviceName('');
        setNewDeviceType('desktop');
      }
    } catch (error) {
      console.error('Error adding device:', error);
    }
  };

  const handleDeleteDevice = async () => {
    if (!selectedDevice) return;

    try {
      const response = await fetch(
        `/api/voice/devices/${selectedDevice.id}?org_id=${orgId}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        setDevices(devices.filter((d) => d.id !== selectedDevice.id));
        setShowDeleteDialog(false);
        setSelectedDevice(null);
      }
    } catch (error) {
      console.error('Error deleting device:', error);
    }
  };

  const handleTogglePause = async (device: Device) => {
    const endpoint =
      device.status === 'active'
        ? `/api/voice/devices/${device.id}/pause`
        : `/api/voice/devices/${device.id}/resume`;

    try {
      const response = await fetch(`${endpoint}?org_id=${orgId}`, {
        method: 'POST',
      });

      if (response.ok) {
        const updated = await response.json();
        setDevices(devices.map((d) => (d.id === device.id ? updated : d)));
      }
    } catch (error) {
      console.error('Error toggling device:', error);
    }
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'desktop':
        return '💻';
      case 'laptop':
        return '🖥️';
      case 'mobile':
        return '📱';
      default:
        return '📱';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800';
      case 'revoked':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Devices</h2>
          <p className="text-gray-600">Manage voice-enabled devices</p>
        </div>

        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add Device
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Device</DialogTitle>
              <DialogDescription>
                Register a new device for voice automation
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Device Name</label>
                <Input
                  placeholder="e.g., Bedroom Desktop"
                  value={newDeviceName}
                  onChange={(e) => setNewDeviceName(e.target.value)}
                  className="mt-1"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Device Type</label>
                <Select value={newDeviceType} onValueChange={setNewDeviceType}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="desktop">Desktop</SelectItem>
                    <SelectItem value="laptop">Laptop</SelectItem>
                    <SelectItem value="mobile">Mobile</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleAddDevice}
                  disabled={!newDeviceName}
                  className="flex-1"
                >
                  Add Device
                </Button>
                <Button
                  onClick={() => setShowAddDialog(false)}
                  variant="outline"
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {devices.length === 0 ? (
        <Card>
          <CardContent className="pt-8 text-center">
            <p className="text-gray-600 mb-4">No devices registered yet</p>
            <Button
              onClick={() => setShowAddDialog(true)}
              variant="outline"
            >
              Register Your First Device
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {devices.map((device) => (
            <Card key={device.id}>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="text-4xl">
                    {getDeviceIcon(device.device_type)}
                  </div>

                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{device.name}</h3>
                    <div className="flex gap-4 text-sm text-gray-600 mt-1">
                      <span>Type: {device.device_type}</span>
                      <span>OS: {device.os_type}</span>
                    </div>
                    <div className="flex gap-2 mt-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(device.status)}`}>
                        {device.status.charAt(0).toUpperCase() + device.status.slice(1)}
                      </span>
                      {device.last_seen && (
                        <span className="text-xs text-gray-500">
                          Last seen: {new Date(device.last_seen).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleTogglePause(device)}
                    >
                      {device.status === 'active' ? (
                        <>
                          <Pause className="w-4 h-4" />
                          Pause
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Resume
                        </>
                      )}
                    </Button>

                    <AlertDialog open={showDeleteDialog && selectedDevice?.id === device.id}>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete Device</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to revoke voice access for{' '}
                            <strong>{device.name}</strong>? This action cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <div className="flex gap-2">
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={handleDeleteDevice}>
                            Delete
                          </AlertDialogAction>
                        </div>
                      </AlertDialogContent>
                    </AlertDialog>

                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-600 hover:text-red-700"
                      onClick={() => {
                        setSelectedDevice(device);
                        setShowDeleteDialog(true);
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default DeviceManager;
