/*
 * Voice Enrollment Wizard Component
 * React component for 3-step voice profile enrollment
 */
import React, { useState, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Mic, CheckCircle2, AlertCircle } from 'lucide-react';
import { getBaseUrl } from '@/lib/api';

interface EnrollmentStep {
  number: number;
  title: string;
  instruction: string;
  prompt: string;
}

const ENROLLMENT_STEPS: EnrollmentStep[] = [
  {
    number: 1,
    title: 'First Sample',
    instruction: 'Record your first voice sample',
    prompt: 'Please say: "My name is [Your Name]"',
  },
  {
    number: 2,
    title: 'Second Sample',
    instruction: 'Record your second voice sample',
    prompt: 'Please say: "Voice automation is awesome"',
  },
  {
    number: 3,
    title: 'Verification',
    instruction: 'Record a final verification sample',
    prompt: 'Please repeat: "I authorize HSBot with voice"',
  },
];

export const VoiceEnrollment: React.FC<{ onComplete?: () => void }> = ({
  onComplete,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordings, setRecordings] = useState<Blob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true },
      });

      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: 'audio/wav',
        });
        setRecordings([...recordings, audioBlob]);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      setError(
        `Failed to access microphone: ${err instanceof Error ? err.message : 'Unknown error'}`
      );
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => {
        track.stop();
      });
    }
    setIsRecording(false);
  };

  const handleNextStep = async () => {
    if (currentStep < ENROLLMENT_STEPS.length) {
      setCurrentStep(currentStep + 1);
    } else {
      // Submit all recordings
      await submitEnrollment();
    }
  };

  const handlePreviousStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const submitEnrollment = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      // Create form data with all recordings
      const formData = new FormData();
      recordings.forEach((recording, index) => {
        formData.append(`audio_${index + 1}`, recording, `sample_${index + 1}.wav`);
      });

      const response = await fetch(`${getBaseUrl()}/voice/enroll`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        setSuccess(true);
        if (onComplete) {
          setTimeout(onComplete, 2000);
        }
      } else {
        const data = await response.json();
        setError(data.detail || 'Enrollment failed');
      }
    } catch (err) {
      setError(
        `Enrollment error: ${err instanceof Error ? err.message : 'Unknown error'}`
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const step = ENROLLMENT_STEPS[currentStep - 1];
  const progress = (currentStep / ENROLLMENT_STEPS.length) * 100;

  if (success) {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardContent className="pt-8">
          <div className="text-center space-y-4">
            <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto" />
            <h2 className="text-2xl font-bold">Enrollment Complete!</h2>
            <p className="text-gray-600">
              Your voice profile has been successfully created. You can now use
              voice commands to control HSBot.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Voice Profile Enrollment</CardTitle>
        <CardDescription>
          Record 3 voice samples to train your voice profile
        </CardDescription>
        <Progress value={progress} className="mt-4" />
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Step Indicator */}
        <div className="flex gap-2">
          {ENROLLMENT_STEPS.map((s) => (
            <button
              key={s.number}
              onClick={() => setCurrentStep(s.number)}
              disabled={s.number > recordings.length + 1}
              className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
                s.number === currentStep
                  ? 'bg-blue-600 text-white'
                  : s.number <= recordings.length
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-200 text-gray-600 cursor-not-allowed'
              }`}
            >
              Step {s.number}
            </button>
          ))}
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 mb-2">{step.instruction}</h3>
          <p className="text-blue-800 font-medium">{step.prompt}</p>
        </div>

        {/* Recording Controls */}
        <div className="space-y-4">
          <div className="flex justify-center">
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              className={`w-20 h-20 rounded-full flex items-center justify-center transition-all ${
                isRecording
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-blue-600 hover:bg-blue-700'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isProcessing ? (
                <Loader2 className="w-8 h-8 text-white animate-spin" />
              ) : (
                <Mic
                  className={`w-8 h-8 text-white ${
                    isRecording ? 'animate-pulse' : ''
                  }`}
                />
              )}
            </button>
          </div>

          {isRecording && (
            <p className="text-center text-red-600 font-medium animate-pulse">
              Recording...
            </p>
          )}

          {recordings.length >= currentStep && (
            <p className="text-center text-green-600 font-medium flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              Sample recorded
            </p>
          )}
        </div>

        {/* Navigation Buttons */}
        <div className="flex gap-3">
          <Button
            onClick={handlePreviousStep}
            disabled={currentStep === 1}
            variant="outline"
            className="flex-1"
          >
            Previous
          </Button>

          <Button
            onClick={handleNextStep}
            disabled={recordings.length < currentStep || isRecording || isProcessing}
            className="flex-1"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : currentStep === ENROLLMENT_STEPS.length ? (
              'Complete Enrollment'
            ) : (
              'Next'
            )}
          </Button>
        </div>

        {/* Tips */}
        <div className="bg-gray-50 p-4 rounded-lg text-sm text-gray-700">
          <h4 className="font-semibold mb-2">Tips for best results:</h4>
          <ul className="space-y-1 list-disc list-inside">
            <li>Speak clearly and naturally</li>
            <li>Minimize background noise</li>
            <li>Use consistent volume</li>
            <li>Face the microphone directly</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};

export default VoiceEnrollment;
