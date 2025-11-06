import '@maxhub/max-ui/dist/styles.css';
import { MaxUI, Panel, Button } from "@maxhub/max-ui";

const App = () => {
  return (
    <MaxUI>
      <Panel centeredX centeredY>
        <Button>
          Hello world!
        </Button>
      </Panel>
    </MaxUI>
  )
}

export default App;  // ← Add this line