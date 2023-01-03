import {ReactNode, useState} from 'react';
import styled from '@emotion/styled';

import {IconAdd, IconSubtract} from 'sentry/icons';
import {t} from 'sentry/locale';
import space from 'sentry/styles/space';

type NodeProps = {
  type: string;
  children?: ReactNode[];
  identifier?: string;
};

function Node({type, identifier, children}: NodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  return (
    <NodeContents>
      {children?.length && (
        <IconWrapper
          aria-label={isExpanded ? t('Collapse') : t('Expand')}
          isExpanded={isExpanded}
          onClick={evt => {
            evt.preventDefault();
            setIsExpanded(!isExpanded);
          }}
        >
          {isExpanded ? (
            <IconSubtract size="9px" color="white" />
          ) : (
            <IconAdd size="9px" color="white" />
          )}
        </IconWrapper>
      )}
      <NodeTitle>{identifier ? `${type} - ${identifier}` : type}</NodeTitle>
      {isExpanded && children}
    </NodeContents>
  );
}

function Tree({hierarchy}) {
  if (!hierarchy.children.length) {
    return <Node type={hierarchy.type} identifier={hierarchy.identifier} />;
  }

  return (
    <Node type={hierarchy.type} identifier={hierarchy.identifier}>
      {hierarchy.children.map(element => (
        <Tree key={element.id} hierarchy={element} />
      ))}
    </Node>
  );
}

function ViewHierarchyContainer({hierarchy}) {
  return (
    <Container>
      <Tree hierarchy={hierarchy} />
    </Container>
  );
}

export {ViewHierarchyContainer as ViewHierarchyTree};

const Container = styled('div')`
  max-height: 500px;
  overflow: auto;
  background-color: ${p => p.theme.surface100};
  border: 1px solid ${p => p.theme.gray100};
  border-radius: ${p => p.theme.borderRadius};
  padding: 9.5px;
`;

const NodeContents = styled('div')`
  margin-left: ${space(0.5)};
  border-left: 1px solid ${p => p.theme.gray200};
  padding-left: ${space(1.5)};

  :first-child {
    margin-left: 0;
    border-left: none;
    padding-left: 0;
  }
`;

// TODO: Clicking the title will open more information
// about the node, currently this does nothing
const NodeTitle = styled('span')`
  cursor: pointer;
`;

const IconWrapper = styled('div')<{isExpanded: boolean}>`
  border-radius: 2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin-right: 4px;
  ${p =>
    p.isExpanded
      ? `
          background: ${p.theme.gray300};
          border: 1px solid ${p.theme.gray300};
          &:hover {
            background: ${p.theme.gray400};
          }
        `
      : `
          background: ${p.theme.blue300};
          border: 1px solid ${p.theme.blue300};
          &:hover {
            background: ${p.theme.blue200};
          }
        `}
`;