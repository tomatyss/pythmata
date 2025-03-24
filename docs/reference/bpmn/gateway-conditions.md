# Gateway Conditions

Gateway conditions allow you to control the flow of your process based on variable values and expressions. This guide explains how to set up and use conditions on gateways in Pythmata.

## Gateway Types and Conditions

Pythmata supports three types of gateways, each with different behavior regarding conditions:

### Exclusive Gateway (XOR)

![Exclusive Gateway](images/exclusive-gateway.svg)

- Only one outgoing path is taken
- The first path with a condition that evaluates to `true` is selected
- If no conditions evaluate to `true`, the default flow is taken (if defined)
- If no default flow is defined and no conditions are true, the process will halt

### Inclusive Gateway (OR)

![Inclusive Gateway](images/inclusive-gateway.svg)

- Multiple outgoing paths can be taken
- All paths with conditions that evaluate to `true` are selected
- If no conditions evaluate to `true`, the default flow is taken (if defined)
- If no default flow is defined and no conditions are true, the process will halt

### Parallel Gateway (AND)

![Parallel Gateway](images/parallel-gateway.svg)

- All outgoing paths are always taken
- Conditions are not used on parallel gateways

## Setting Up Gateway Properties

### Gateway Configuration Panel

When you select a gateway in your process diagram, you'll see a "Gateway" tab in the properties panel. This tab provides gateway-specific configuration options:

1. For exclusive and inclusive gateways, you can select a default flow
2. The default flow is taken when no conditions evaluate to true
3. Parallel gateways do not have configuration options since they activate all outgoing flows

### Setting Up Conditions

To set up conditions on gateway sequence flows:

1. Create a gateway in your process diagram
2. Add outgoing sequence flows from the gateway to other elements
3. Select a sequence flow connected to a gateway
4. In the properties panel, you'll see the "Flow Condition" section
5. Enter your condition expression or set the flow as the default flow

You can configure the default flow either from the gateway properties panel or from the sequence flow properties panel.

## Condition Expression Syntax

Conditions in Pythmata use the following syntax:

```
${expression}
```

Where `expression` is a JavaScript expression that evaluates to a boolean value.

### Examples

- `${amount > 1000}`
- `${status == 'approved'}`
- `${priority == 'high' || category == 'special'}`
- `${amount > 1000 && status == 'approved'}`

## Using Process Variables

Your conditions can reference any process variables that have been defined. These variables are available in the expression context.

For example, if you have defined a process variable called `amount`, you can use it in a condition like this:

```
${amount > 1000}
```

## Default Flows

A default flow is taken when no other conditions evaluate to `true`. To set a sequence flow as the default:

1. Select the sequence flow
2. In the properties panel, check "Use as default flow"

A default flow cannot have a condition expression.

## Best Practices

- Always define a default flow for exclusive and inclusive gateways
- Keep conditions simple and readable
- Use meaningful variable names
- Test your conditions with different variable values
- For complex conditions, consider using a script task to prepare a boolean variable, then use that variable in a simple condition

## Troubleshooting

If your gateway conditions are not working as expected:

- Check that your variables are correctly defined and populated
- Verify the syntax of your condition expressions
- Ensure that the gateway type matches your intended behavior
- Check the process logs for evaluation errors
