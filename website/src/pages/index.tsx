import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import Heading from '@theme/Heading';
import styles from './index.module.css';

export default function Home(): ReactNode {
  return (
    <Layout
      title="Local AI Assistant"
      description="Documentation for a local AI assistant">
      <header className={styles.hero}>
        <div className="container">
          <Heading as="h1">Local AI Assistant</Heading>
          <p>
            Run an AI assistant locally, use local models, and retrieve
            information from your own documentation and files.
          </p>

          <div className={styles.buttons}>
            <Link
              className="button button--primary button--lg"
              to="/docs/getting-started/overview">
              Read the documentation
            </Link>

            <Link
              className="button button--secondary button--lg"
              to="/docs/getting-started/quickstart">
              Quick start
            </Link>
          </div>
        </div>
      </header>
    </Layout>
  );
}

