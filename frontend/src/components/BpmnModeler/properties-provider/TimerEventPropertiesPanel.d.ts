import { FC } from 'react';

interface TimerEventPropertiesPanelProps {
  element: {
    id: string;
    type: string;
    businessObject: {
      id: string;
      eventDefinitions?: Array<{
        $type: string;
        timeDuration?: { body: string };
        timeDate?: { body: string };
        timeCycle?: { body: string };
      }>;
      extensionElements?: {
        values: Array<{
          $type: string;
          timerType?: string;
          timerValue?: string;
        }>;
      };
    };
  };
  modeler: {
    get: <T>(name: string) => T;
  };
}

declare const TimerEventPropertiesPanel: FC<TimerEventPropertiesPanelProps>;

export default TimerEventPropertiesPanel;
